## Pubsublite to GCS

Template for reading files from Pub/Sub lite and writing them to Google Cloud Storage. It supports writing JSON, CSV, Parquet and Avro formats.


## Arguments

* `pubsublite.to.gcs.input.subscription`: Pubsublite Input Subscription Name
* `pubsublite.to.gcs.write.mode`: Output write mode (one of: append,overwrite,ignore,errorifexists)(Defaults to append)
* `pubsublite.to.gcs.output.location`: GCS Location to put Output Files (format: `gs://BUCKET/...`)
* `pubsublite.to.gcs.checkpoint.location`: GCS Checkpoint Folder Location
* `pubsublite.to.gcs.output.format`: GCS Output File Format (one of: avro,parquet,csv,json)(Defaults to csv)

## Usage

```
$ python main.py --template PUBSUBLITETOGCS --help

usage: main.py --template PUBSUBLITETOGCS [-h] \
	--pubsublite.to.gcs.input.subscription PUBSUBLITE.GCS.INPUT.SUBSCRIPTION \
	--pubsublite.to.gcs.output.location PUBSUBLITE.GCS.OUTPUT.LOCATION \
	--pubsublite.to.gcs.checkpoint.location PUBSUBLITE.GCS.CHECKPOINT.LOCATION \

optional arguments:
  -h, --help            show this help message and exit
  --pubsublite.to.gcs.write.mode PUBSUBLITE.TO.GCS.WRITE.MODE 
            {avro,parquet,csv,json} Output Format (Defaults to csv)
  --pubsublite.to.gcs.output.format PUBSUBLITE.TO.GCS.OUTPUT.FORMAT
            {overwrite,append,ignore,errorifexists} Output Write Mode (Defaults to append)
```

## Required JAR files

It uses the [Pubsublite Spark SQL Streaming](https://central.sonatype.com/artifact/com.google.cloud/pubsublite-spark-sql-streaming/1.0.0) for reading data from Pub/Sub lite to be available in the Dataproc cluster.

## Example submission

```
export GCP_PROJECT=my-project
export JARS="gs://spark-lib/pubsublite/pubsublite-spark-sql-streaming-1.0.0.jar"
export GCS_STAGING_LOCATION="gs://my-bucket"
export REGION=us-central1
	
./bin/start.sh \
-- --template=PUBSUBLITETOGCS \
    --pubsublite.to.gcs.input.subscription=projects/my-project/locations/us-central1/subscriptions/pubsublite-subscription",
    --pubsublite.to.gcs.write.mode=append",
    --pubsublite.to.gcs.output.location=gs://outputLocation",
    --pubsublite.to.gcs.checkpoint.location=gs://checkpointLocation",
    --pubsublite.to.gcs.output.format=csv"
```