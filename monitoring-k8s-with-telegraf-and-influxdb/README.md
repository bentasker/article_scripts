# Monitoring Kubernetes with InfluxDB, Telegraf and Grafana

This directory contains files associated with the post [Deploying InfluxDB and Telegraf to monitor Kubernetes](https://www.bentasker.co.uk/posts/documentation/kubernetes/monitoring-k8s-with-telegraf-and-influxdb.html).

----

### Pre-Requisites

I use NFS to back my physical volumes. Even if you're doing the same, you're probably not making shares available at the same address and path, so before applying `influxdb-kubemonitoring.yml` you'll want to edit the PVs near the top.

You'll also need to create the secret referred to, with a command like

```sh
kubectl create namespace monitoring

kubectl -n monitoring create secret generic influxdb-info \
--from-literal=user=influxadmin \
--from-literal=password='CHANGEME' \
--from-literal=org="kubernetes" \
--from-literal=token="CHANGEME" \
--from-literal=readuser="kubestatsro" \
--from-literal=readpass="CHANGEME" \
--from-literal=writeuser="kubestatsw" \
--from-literal=writepass="CHANGEME" \
```

If you want to enable [Edge Data replication](https://www.influxdata.com/products/influxdb-edge-data-replication/) then you'll need to create a second secret containing details of your upstream InfluxDB instance
```sh
kubectl -n monitoring create secret generic upstream-influxdb \
--from-literal=url='<URL>' \
--from-literal=org="<ORG>" \
--from-literal=token="<TOKEN>" \
--from-literal=bucket="<BUCKET>"
```

You _should_ then just be able to apply the manifests to create the resources

```sh
kubectl apply -f influxdb-kubemonitoring.yml
```

Once applied, you should see a service
```sh
kubectl -n monitoring get svc 
```

You can use the listed cluster IP to access InfluxDB's interface or when [configuring in Grafana](https://www.bentasker.co.uk/posts/documentation/kubernetes/monitoring-k8s-with-telegraf-and-influxdb.html#dashboarding)

----

### Grafana dashboard 

The Dashboard template in this repo ([`Kubernetes_Resource_usage.json`](Kubernetes_Resource_usage.json) is the dashboard screenshotted in my post. 

To install:

* Download a copy of [`Kubernetes_Resource_usage.json`](Kubernetes_Resource_usage.json)
* Log into Grafana
* Create your datasource
* Browse to Dashboards
* Click the arrow on the `New` button and select `Import`
* Upload the JSON file 
* Select the appropriate datasource

You _should_ be good to go.

---

### License

Copyright (c) B Tasker, 2024. Released under a [BSD 3-Clause License](https://www.bentasker.co.uk/pages/licenses/bsd-3-clause.html)
