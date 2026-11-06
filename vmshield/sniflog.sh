#!/usr/bin/env bash
# 记录 VM 访问的域名：TLS SNI (443) / HTTP Host (80) / DNS 查询
# 输出: /var/log/vmshield-sni.log  格式 时间|源IP|SNI|Host|DNS查询
exec /usr/bin/tshark -i virbr0 -l -n -q \
  -f "ether host 52:54:00:3c:84:c7 and (tcp port 443 or tcp port 80 or udp port 53)" \
  -Y "tls.handshake.type==1 or http.request or dns.flags.response==0" \
  -T fields -e frame.time -e ip.src -e tls.handshake.extensions_server_name -e http.host -e dns.qry.name \
  -E separator='|' -E occurrence=f
