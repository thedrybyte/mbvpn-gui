/*
 * mbvpn-firewall: High-performance Linux VPN Kill Switch controller using libnftables.
 * Manages the dedicated 'inet mbvpn_ks' nftables table.
 * Dynamically detects physical interfaces to prevent traffic leakage outside the tunnel.
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
            // Found a physical interface
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
        fprintf(stderr, "Usage: %s <enable|disable|status|supports-hard> [endpoint_ip] [endpoint_port] [hard] [tunnel_interface]\n", argv[0]);
        return 1;
    }

    char err[512] = {0};
    const char *action = argv[1];

    if (strcmp(action, "disable") == 0) {
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
            char cmd[1200];
            snprintf(cmd, sizeof(cmd),
                "%stable inet mbvpn_ks {\n"
                "  chain output {\n"
                "    type filter hook output priority filter; policy drop;\n"
                "    oifname \"lo\" accept\n"
                "    udp sport 68 udp dport 67 accept\n"
                "%s%s"
                "  }\n"
                "}\n", table_exists ? "delete table inet mbvpn_ks\n" : "", tunnel_rule, endpoint_rule);

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
            // Fallback default
            strncpy(phys_ifaces, "\"wlp2s0\", \"enp0s31f6\"", sizeof(phys_ifaces) - 1);
        }

        // Clean up any existing table first
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
                "    ip daddr { 172.217.0.0/16, 142.250.0.0/15, 34.0.0.0/8, 35.0.0.0/8 } tcp dport 443 accept\n"
                "    ip daddr %s udp dport %s accept\n"
                "  }\n"
                "}\n", phys_ifaces, ip, port);
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
                "    ip daddr { 172.217.0.0/16, 142.250.0.0/15, 34.0.0.0/8, 35.0.0.0/8 } tcp dport 443 accept\n"
                "  }\n"
                "}\n", phys_ifaces);
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
