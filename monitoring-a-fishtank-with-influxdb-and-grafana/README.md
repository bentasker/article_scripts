# Aquarium Monitoring Scripts

Copy of scripts referred to in [Monitoring an Aquarium with InfluxDB and Grafana](https://www.bentasker.co.uk/posts/blog/house-stuff/monitoring-a-fishtank-with-influxdb-and-grafana.html)

They read from temperature (DS18B20) and waterflow (FL-408) sensors and then write line protocol into an InfluxDB instance.

Alternatively, they can write into a Telegraf instance to benefit from its buffering capabilities - `telegraf/docker-compose.yml` and `telegraf/telegraf.conf` provide the means for this.

Scripts are released under a [BSD 3-Clause License](https://www.bentasker.co.uk/pages/licenses/bsd-3-clause.html)
