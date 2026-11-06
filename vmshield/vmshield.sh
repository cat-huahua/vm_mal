#!/usr/bin/env bash
# vmshield —— 宿主机侧的 libvirt 虚拟机出口白名单
# 用法: vmshield.sh {on|off|status|watch|log}
set -euo pipefail

VM_MAC="${VM_MAC:-52:54:00:3c:84:c7}"   # 按 MAC 识别，DHCP 换 IP 也不会失效
LAN="${LAN:-192.168.3.0/24}"
IFACE="${IFACE:-virbr0}"
NFT=/usr/sbin/nft

rules() {
cat <<EOF
table inet vmshield {
  chain forward {
    type filter hook forward priority 0; policy accept;
    # 1) 一律禁止碰内网（路由器/NAS/打印机/其它机器）
    ether saddr $VM_MAC ip daddr $LAN counter log prefix "vmshield-LAN " limit rate 5/second drop
    # 2) 已建立的连接回程放行
    ether saddr $VM_MAC ct state established,related counter accept
    # 3) 只放行网页：HTTP/HTTPS/DNS/ICMP（Edge 和浏览器下载都走这里）
    ether saddr $VM_MAC tcp dport { 80, 443 } counter accept
    ether saddr $VM_MAC udp dport 53 counter accept
    ether saddr $VM_MAC ip protocol icmp counter accept
    # 4) 其它一律丢弃并记录
    ether saddr $VM_MAC counter log prefix "vmshield-DROP " limit rate 10/second drop
  }
  chain input {
    type filter hook input priority 0; policy accept;
    # VM 只能问 DNS 和要 DHCP，其它一律不许碰宿主机
    ether saddr $VM_MAC ip daddr 192.168.122.1 udp dport 53 counter accept
    ether saddr $VM_MAC ip daddr 192.168.122.1 tcp dport 53 counter accept
    ether saddr $VM_MAC udp dport 67 counter accept
    ether saddr $VM_MAC ip saddr 192.168.122.0/24 counter log prefix "vmshield-HOST " limit rate 5/second drop
  }
}
EOF
}

case "${1:-status}" in
  on)
    $NFT delete table inet vmshield 2>/dev/null || true
    rules | $NFT -f -
    echo "vmshield 已启用：VM 只能 80/443/53/ICMP；内网 $LAN 与宿主机 192.168.122.1 全拦"
    ;;
  off)
    $NFT delete table inet vmshield 2>/dev/null && echo "vmshield 已关闭" || echo "vmshield 本来就没开"
    ;;
  status)
    $NFT list table inet vmshield 2>/dev/null || { echo "vmshield 未启用"; exit 0; }
    ;;
  watch)
    echo "监听 $IFACE 上 VM 的所有流量（Ctrl-C 退出）…"
    sudo tcpdump -ni "$IFACE" "ether host $VM_MAC" -vv
    ;;
  log)
    sudo journalctl -k -f -n 50 | grep --line-buffered "vmshield-"
    ;;
  sni)
    echo "实时域名日志（Ctrl-C 退出）："
    sudo tail -f /var/log/vmshield-sni.log
    ;;
  *)
    echo "用法: $0 {on|off|status|watch|log|sni}"; exit 1 ;;
esac
