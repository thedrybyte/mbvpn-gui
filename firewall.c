/*
 * mbvpn-firewall: High-performance Linux VPN Kill Switch & Split Tunnel controller using libnftables & Netlink.
 * Manages the dedicated 'inet mbvpn_ks' nftables table.
 * Dynamically detects physical interfaces to prevent traffic leakage outside the tunnel.
 * Manages kernel routing table for website / IP split-tunneling (proto 77).
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <dirent.h>
#include <unistd.h>
#include <nftables/libnftables.h>
#include <linux/rtnetlink.h>
#include <sys/socket.h>

#define SPLIT_TUNNEL_PROTO 77

static int get_physical_interfaces(char *buf, size_t buflen) {
    DIR *d = opendir("/sys/class/net");
    if (!d) return -1;

    struct dirent *dir;
    buf[0] = '\0';
    int count = 0;

    while ((dir = readdir(d)) != NULL) {
        if (dir->d_name[0] == '.') continue;
        char dev_path[512];
        snprintf(dev_path, sizeof(dev_path), "/sys/class/net/%s/device", dir->d_name);
        if (access(dev_path, F_OK) == 0) {
            if (count > 0) {
                strncat(buf, ", ", buflen - strlen(buf) - 1);
            }
            strncat(buf, "\"", buflen - strlen(buf) - 1);
            strncat(buf, dir->d_name, buflen - strlen(buf) - 1);
            strncat(buf, "\"", buflen - strlen(buf) - 1);
            count++;
        }
    }
    closedir(d);
    return count;
}

static int get_default_gw(char *gw_buf, size_t gw_len, char *iface_buf, size_t iface_len) {
    FILE *f = fopen("/proc/net/route", "r");
    if (!f) return -1;
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        char iface[64];
        unsigned long dest, gw, flags;
        if (sscanf(line, "%63s %lx %lx %lx", iface, &dest, &gw, &flags) == 4) {
            if (dest == 0 && (flags & 0x2)) {
                if (strncmp(iface, "wg-", 3) != 0 && strncmp(iface, "mbvpn", 5) != 0) {
                    struct in_addr addr;
                    addr.s_addr = gw;
                    snprintf(gw_buf, gw_len, "%s", inet_ntoa(addr));
                    snprintf(iface_buf, iface_len, "%s", iface);
                    fclose(f);
                    return 0;
                }
            }
        }
    }
    fclose(f);
    return -1;
}

static int add_route(const char *ip_str, const char *gw_str, const char *ifname) {
    char auto_gw[64] = {0};
    char auto_if[64] = {0};
    if (!gw_str || !ifname || strlen(gw_str) == 0 || strlen(ifname) == 0) {
        if (get_default_gw(auto_gw, sizeof(auto_gw), auto_if, sizeof(auto_if)) != 0) {
            fprintf(stderr, "ERROR: Could not detect default gateway\n");
            return -1;
        }
        gw_str = auto_gw;
        ifname = auto_if;
    }

    int fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    if (fd < 0) return -1;

    char ip_copy[128];
    strncpy(ip_copy, ip_str, sizeof(ip_copy) - 1);
    ip_copy[sizeof(ip_copy) - 1] = '\0';
    int prefix_len = 32;
    char *slash = strchr(ip_copy, '/');
    if (slash) {
        *slash = '\0';
        prefix_len = atoi(slash + 1);
        if (prefix_len < 0 || prefix_len > 32) prefix_len = 32;
    }

    struct in_addr dst, gw;
    if (inet_pton(AF_INET, ip_copy, &dst) != 1 || inet_pton(AF_INET, gw_str, &gw) != 1) {
        close(fd);
        return -1;
    }
    unsigned int ifindex = if_nametoindex(ifname);
    if (!ifindex) {
        close(fd);
        return -1;
    }

    char buf[512] = {0};
    struct nlmsghdr *nlh = (struct nlmsghdr *)buf;
    nlh->nlmsg_len = NLMSG_LENGTH(sizeof(struct rtmsg));
    nlh->nlmsg_type = RTM_NEWROUTE;
    nlh->nlmsg_flags = NLM_F_REQUEST | NLM_F_CREATE | NLM_F_REPLACE | NLM_F_ACK;
    nlh->nlmsg_seq = 1;

    struct rtmsg *rtm = (struct rtmsg *)NLMSG_DATA(nlh);
    rtm->rtm_family = AF_INET;
    rtm->rtm_dst_len = prefix_len;
    rtm->rtm_table = RT_TABLE_MAIN;
    rtm->rtm_protocol = SPLIT_TUNNEL_PROTO;
    rtm->rtm_scope = RT_SCOPE_UNIVERSE;
    rtm->rtm_type = RTN_UNICAST;

    struct rtattr *rta = (struct rtattr *)((char *)nlh + NLMSG_ALIGN(nlh->nlmsg_len));
    rta->rta_type = RTA_DST;
    rta->rta_len = RTA_LENGTH(sizeof(dst));
    memcpy(RTA_DATA(rta), &dst, sizeof(dst));
    nlh->nlmsg_len = NLMSG_ALIGN(nlh->nlmsg_len) + RTA_ALIGN(rta->rta_len);

    rta = (struct rtattr *)((char *)nlh + NLMSG_ALIGN(nlh->nlmsg_len));
    rta->rta_type = RTA_GATEWAY;
    rta->rta_len = RTA_LENGTH(sizeof(gw));
    memcpy(RTA_DATA(rta), &gw, sizeof(gw));
    nlh->nlmsg_len = NLMSG_ALIGN(nlh->nlmsg_len) + RTA_ALIGN(rta->rta_len);

    rta = (struct rtattr *)((char *)nlh + NLMSG_ALIGN(nlh->nlmsg_len));
    rta->rta_type = RTA_OIF;
    rta->rta_len = RTA_LENGTH(sizeof(ifindex));
    memcpy(RTA_DATA(rta), &ifindex, sizeof(ifindex));
    nlh->nlmsg_len = NLMSG_ALIGN(nlh->nlmsg_len) + RTA_ALIGN(rta->rta_len);

    struct sockaddr_nl sa;
    memset(&sa, 0, sizeof(sa));
    sa.nl_family = AF_NETLINK;

    if (sendto(fd, nlh, nlh->nlmsg_len, 0, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        close(fd);
        return -1;
    }

    char reply[1024];
    int len = recv(fd, reply, sizeof(reply), 0);
    close(fd);
    if (len > 0) {
        struct nlmsghdr *r = (struct nlmsghdr *)reply;
        if (r->nlmsg_type == NLMSG_ERROR) {
            struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(r);
            if (err->error != 0) return -1;
        }
    }
    printf("OK: Route added %s via %s dev %s\n", ip_str, gw_str, ifname);
    return 0;
}

static int del_route(const char *ip_str) {
    int fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    if (fd < 0) return -1;

    char ip_copy[128];
    strncpy(ip_copy, ip_str, sizeof(ip_copy) - 1);
    ip_copy[sizeof(ip_copy) - 1] = '\0';
    int prefix_len = 32;
    char *slash = strchr(ip_copy, '/');
    if (slash) {
        *slash = '\0';
        prefix_len = atoi(slash + 1);
        if (prefix_len < 0 || prefix_len > 32) prefix_len = 32;
    }

    struct in_addr dst;
    if (inet_pton(AF_INET, ip_copy, &dst) != 1) {
        close(fd);
        return -1;
    }

    char buf[512] = {0};
    struct nlmsghdr *nlh = (struct nlmsghdr *)buf;
    nlh->nlmsg_len = NLMSG_LENGTH(sizeof(struct rtmsg));
    nlh->nlmsg_type = RTM_DELROUTE;
    nlh->nlmsg_flags = NLM_F_REQUEST | NLM_F_ACK;
    nlh->nlmsg_seq = 1;

    struct rtmsg *rtm = (struct rtmsg *)NLMSG_DATA(nlh);
    rtm->rtm_family = AF_INET;
    rtm->rtm_dst_len = prefix_len;
    rtm->rtm_table = RT_TABLE_MAIN;

    struct rtattr *rta = (struct rtattr *)((char *)nlh + NLMSG_ALIGN(nlh->nlmsg_len));
    rta->rta_type = RTA_DST;
    rta->rta_len = RTA_LENGTH(sizeof(dst));
    memcpy(RTA_DATA(rta), &dst, sizeof(dst));
    nlh->nlmsg_len = NLMSG_ALIGN(nlh->nlmsg_len) + RTA_ALIGN(rta->rta_len);

    struct sockaddr_nl sa;
    memset(&sa, 0, sizeof(sa));
    sa.nl_family = AF_NETLINK;

    if (sendto(fd, nlh, nlh->nlmsg_len, 0, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        close(fd);
        return -1;
    }

    char reply[1024];
    int len = recv(fd, reply, sizeof(reply), 0);
    close(fd);
    if (len > 0) {
        struct nlmsghdr *r = (struct nlmsghdr *)reply;
        if (r->nlmsg_type == NLMSG_ERROR) {
            struct nlmsgerr *err = (struct nlmsgerr *)NLMSG_DATA(r);
            if (err->error != 0) return -1;
        }
    }
    printf("OK: Route deleted %s\n", ip_str);
    return 0;
}

static int flush_routes(void) {
    int fd = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE);
    if (fd < 0) return -1;

    char buf[8192];
    memset(buf, 0, sizeof(buf));
    struct nlmsghdr *nlh = (struct nlmsghdr *)buf;
    nlh->nlmsg_len = NLMSG_LENGTH(sizeof(struct rtmsg));
    nlh->nlmsg_type = RTM_GETROUTE;
    nlh->nlmsg_flags = NLM_F_REQUEST | NLM_F_DUMP;
    nlh->nlmsg_seq = 1;

    struct rtmsg *rtm = (struct rtmsg *)NLMSG_DATA(nlh);
    rtm->rtm_family = AF_INET;

    struct sockaddr_nl sa;
    memset(&sa, 0, sizeof(sa));
    sa.nl_family = AF_NETLINK;

    if (sendto(fd, nlh, nlh->nlmsg_len, 0, (struct sockaddr *)&sa, sizeof(sa)) < 0) {
        close(fd);
        return -1;
    }

    int count = 0;
    while (1) {
        char reply[8192];
        int len = recv(fd, reply, sizeof(reply), 0);
        if (len <= 0) break;
        struct nlmsghdr *msg = (struct nlmsghdr *)reply;
        int done = 0;
        for (; NLMSG_OK(msg, len); msg = NLMSG_NEXT(msg, len)) {
            if (msg->nlmsg_type == NLMSG_DONE) {
                done = 1;
                break;
            }
            if (msg->nlmsg_type == NLMSG_ERROR) {
                done = 1;
                break;
            }
            if (msg->nlmsg_type == RTM_NEWROUTE) {
                struct rtmsg *r = (struct rtmsg *)NLMSG_DATA(msg);
                if (r->rtm_family == AF_INET && r->rtm_protocol == SPLIT_TUNNEL_PROTO) {
                    struct rtattr *attr = (struct rtattr *)RTM_RTA(r);
                    int attr_len = RTM_PAYLOAD(msg);
                    for (; RTA_OK(attr, attr_len); attr = RTA_NEXT(attr, attr_len)) {
                        if (attr->rta_type == RTA_DST) {
                            struct in_addr *dst = (struct in_addr *)RTA_DATA(attr);
                            char ip_buf[INET_ADDRSTRLEN];
                            inet_ntop(AF_INET, dst, ip_buf, sizeof(ip_buf));
                            char ip_cidr[64];
                            snprintf(ip_cidr, sizeof(ip_cidr), "%s/%d", ip_buf, r->rtm_dst_len);
                            del_route(ip_cidr);
                            count++;
                        }
                    }
                }
            }
        }
        if (done) break;
    }
    close(fd);
    printf("OK: Flushed %d split tunnel routes\n", count);
    return 0;
}

static int run_nft(const char *cmd, char *errbuf, size_t errlen) {
    struct nft_ctx *nft = nft_ctx_new(NFT_CTX_DEFAULT);
    if (!nft) {
        if (errbuf) snprintf(errbuf, errlen, "Failed to create nftables context");
        return -1;
    }
    nft_ctx_output_set_flags(nft, NFT_CTX_OUTPUT_ECHO);
    int rc = nft_run_cmd_from_buffer(nft, cmd);
    const char *err = nft_ctx_get_error_buffer(nft);
    if (err && *err && errbuf) {
        snprintf(errbuf, errlen, "%s", err);
    }
    nft_ctx_free(nft);
    return rc;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <enable|disable|status|supports-hard|route-add|route-del|route-flush> [args...]\n", argv[0]);
        return 1;
    }

    char err[512] = {0};
    const char *action = argv[1];

    if (strcmp(action, "route-add") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: %s route-add <ip_or_cidr> [gw] [iface]\n", argv[0]);
            return 1;
        }
        const char *gw = argc > 3 ? argv[3] : NULL;
        const char *iface = argc > 4 ? argv[4] : NULL;
        return add_route(argv[2], gw, iface);
    } else if (strcmp(action, "route-del") == 0) {
        if (argc < 3) {
            fprintf(stderr, "Usage: %s route-del <ip_or_cidr>\n", argv[0]);
            return 1;
        }
        return del_route(argv[2]);
    } else if (strcmp(action, "route-flush") == 0) {
        return flush_routes();
    } else if (strcmp(action, "disable") == 0) {
        int rc = run_nft("delete table inet mbvpn_ks", err, sizeof(err));
        if (rc == 0) {
            printf("OK: Kill switch disabled\n");
            return 0;
        } else {
            if (strstr(err, "No such file") || strstr(err, "does not exist") || strstr(err, "ENOENT")) {
                printf("OK: Kill switch was not active\n");
                return 0;
            }
            fprintf(stderr, "ERROR: %s\n", err);
            return rc;
        }
    } else if (strcmp(action, "status") == 0) {
        int rc = run_nft("list table inet mbvpn_ks", err, sizeof(err));
        if (rc == 0) {
            printf("ACTIVE\n");
            return 0;
        } else {
            printf("INACTIVE\n");
            return 0;
        }
    } else if (strcmp(action, "supports-hard") == 0) {
        printf("SUPPORTED\n");
        return 0;
    } else if (strcmp(action, "enable") == 0) {
        const char *ip = (argc >= 3 && strlen(argv[2]) > 0) ? argv[2] : NULL;
        const char *port = (argc >= 4 && strlen(argv[3]) > 0) ? argv[3] : "51820";
        int hard = argc >= 5 && strcmp(argv[4], "hard") == 0;
        const char *tunnel_iface = argc >= 6 && strlen(argv[5]) > 0 ? argv[5] : NULL;
        const char *bypass_ips = argc >= 7 && strlen(argv[6]) > 0 ? argv[6] : NULL;

        char bypass_rule[1024] = {0};
        if (bypass_ips) {
            char sanitized[512] = {0};
            size_t s_idx = 0;
            for (size_t i = 0; bypass_ips[i] && s_idx < sizeof(sanitized) - 1; i++) {
                char ch = bypass_ips[i];
                if (isdigit((unsigned char)ch) || ch == '.' || ch == '/' || ch == ',' || ch == ' ') {
                    sanitized[s_idx++] = ch;
                }
            }
            if (s_idx > 0) {
                snprintf(bypass_rule, sizeof(bypass_rule), "    ip daddr { %s } accept\n", sanitized);
            }
        }

        if (hard) {
            char endpoint_rule[256] = {0};
            char tunnel_rule[IFNAMSIZ + 64] = {0};
            struct in_addr endpoint_addr;

            if (ip) {
                char *port_end = NULL;
                long port_number = strtol(port, &port_end, 10);
                if (inet_pton(AF_INET, ip, &endpoint_addr) != 1 || !port_end || *port_end || port_number < 1 || port_number > 65535) {
                    fprintf(stderr, "ERROR: Invalid WireGuard endpoint\n");
                    return 1;
                }
                snprintf(endpoint_rule, sizeof(endpoint_rule), "    ip daddr %s udp dport %ld accept\n", ip, port_number);
            }

            if (tunnel_iface) {
                size_t iface_len = strlen(tunnel_iface);
                if (iface_len >= IFNAMSIZ) {
                    fprintf(stderr, "ERROR: Invalid VPN interface name\n");
                    return 1;
                }
                for (size_t i = 0; i < iface_len; i++) {
                    if (!isalnum((unsigned char)tunnel_iface[i]) && tunnel_iface[i] != '_' && tunnel_iface[i] != '-' && tunnel_iface[i] != '.') {
                        fprintf(stderr, "ERROR: Invalid VPN interface name\n");
                        return 1;
                    }
                }
                snprintf(tunnel_rule, sizeof(tunnel_rule), "    oifname \"%s\" accept\n", tunnel_iface);
            }

            char existing[512] = {0};
            int table_exists = run_nft("list table inet mbvpn_ks", existing, sizeof(existing)) == 0;
            char cmd[2048];
            snprintf(cmd, sizeof(cmd),
                "%stable inet mbvpn_ks {\n"
                "  chain output {\n"
                "    type filter hook output priority filter; policy drop;\n"
                "    oifname \"lo\" accept\n"
                "    udp sport 68 udp dport 67 accept\n"
                "%s%s%s"
                "  }\n"
                "}\n", table_exists ? "delete table inet mbvpn_ks\n" : "", tunnel_rule, endpoint_rule, bypass_rule);

            int rc = run_nft(cmd, err, sizeof(err));
            if (rc == 0) {
                printf("OK: Hard kill switch enabled (VPN-only traffic)\n");
                return 0;
            }
            fprintf(stderr, "ERROR: %s\n", err);
            return rc;
        }

        char phys_ifaces[512] = {0};
        int num_phys = get_physical_interfaces(phys_ifaces, sizeof(phys_ifaces));
        if (num_phys <= 0) {
            strncpy(phys_ifaces, "\"wlp2s0\", \"enp0s31f6\"", sizeof(phys_ifaces) - 1);
        }

        run_nft("delete table inet mbvpn_ks", NULL, 0);

        char cmd[4096];
        if (ip) {
            snprintf(cmd, sizeof(cmd),
                "table inet mbvpn_ks {\n"
                "  chain output {\n"
                "    type filter hook output priority filter; policy drop;\n"
                "    oifname \"lo\" accept\n"
                "    ct state established,related accept\n"
                "    oifname != { %s } accept\n"
                "    ip daddr { 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 255.255.255.255 } accept\n"
                "    ip6 daddr { fe80::/10, ff02::/16 } accept\n"
                "    udp dport { 67, 68 } accept\n"
                "    udp dport 53 accept\n"
                "    tcp dport 53 accept\n"
                "%s"
                "    ip daddr %s udp dport %s accept\n"
                "  }\n"
                "}\n", phys_ifaces, bypass_rule, ip, port);
        } else {
            snprintf(cmd, sizeof(cmd),
                "table inet mbvpn_ks {\n"
                "  chain output {\n"
                "    type filter hook output priority filter; policy drop;\n"
                "    oifname \"lo\" accept\n"
                "    ct state established,related accept\n"
                "    oifname != { %s } accept\n"
                "    ip daddr { 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, 255.255.255.255 } accept\n"
                "    ip6 daddr { fe80::/10, ff02::/16 } accept\n"
                "    udp dport { 67, 68 } accept\n"
                "    udp dport 53 accept\n"
                "    tcp dport 53 accept\n"
                "%s"
                "  }\n"
                "}\n", phys_ifaces, bypass_rule);
        }

        int rc = run_nft(cmd, err, sizeof(err));
        if (rc == 0) {
            printf("OK: Kill switch enabled with physical interfaces: %s\n", phys_ifaces);
            return 0;
        } else {
            fprintf(stderr, "ERROR: %s\n", err);
            return rc;
        }
    } else {
        fprintf(stderr, "Unknown command: %s\n", action);
        return 1;
    }
}
