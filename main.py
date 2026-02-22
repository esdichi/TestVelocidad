import speedtest

st = speedtest.Speedtest()
st.get_best_server()

download = st.download() / 1_000_000
upload = st.upload() / 1_000_000
ping = st.results.ping

print(f"Download: {download:.2f} Mbps")
print(f"Upload: {upload:.2f} Mbps")
print(f"Ping: {ping} ms")
