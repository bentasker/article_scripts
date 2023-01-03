option task = {
    name: "downsample_webmention_raw_stats",
    every: 15m,
    offset: 1m,
    concurrency: 1,
}

in_bucket = "webmentions"
out_bucket = "telegraf/autogen"
host="http://192.168.13.184:8086"
token=""
window_period = 5m


sourcedata = from(bucket: in_bucket, host: host, token: token)
    |> range(start: -1h)
    |> filter(fn: (r) => r._measurement == "webmentions")
    |> filter(fn: (r) => r._field == "id")

// Mention counts
sourcedata
    // Drop the source username from the group key
    |> group(columns: ["_measurement", "type", "url", "domain", "srcdomain"])
    |> aggregateWindow(every: window_period, fn: count, createEmpty: false)
    |> set(key: "_field", value: "mentions")
    |> drop(columns: ["_start", "_stop"])
    |> to(bucket: out_bucket, host: host, token: token)

// Calculate number of unique authors    
sourcedata
    |> window(every: window_period)
    |> group(columns: ["_measurement", "type", "url", "domain", "srcdomain", "author"])
    |> map(fn: (r) => ({r with _value: 1}))
    |> group(columns: ["_measurement", "type", "url", "domain", "srcdomain"])
    |> aggregateWindow(every: window_period, fn: sum, createEmpty: false)
    |> drop(columns: ["_start", "_stop"])
    |> set(key: "_field", value: "num_authors")
    |> to(bucket: out_bucket, host: host, token: token) 
