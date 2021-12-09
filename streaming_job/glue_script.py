import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql.types import StructType, StructField, StringType

source_schema_tweet = StructType([
    StructField('id', StringType(), False),
    StructField('text', StringType(), False),
    StructField('rule_id', StringType(), False),
    StructField('datetime', StringType(), False),
])

def process(df, epoch_id, args):
    print('Process Start')
    df.persist()
    
    df.show(100, truncate=False)

    df.unpersist(blocking=True)
    print('Process End')

def main(args):
    print('Main')
    print(f'  args = {args}')

    glueContext = GlueContext(SparkContext())
    Job(glueContext).init(args['JOB_NAME'],args)
    spark = glueContext.spark_session

    bucket = args['BUCKET']

    source_path = f's3://{bucket}/stream/tweet/*/*/*/*/*/*/*'
    source_mode = 'FAILFAST'
    source_files = 10
    source_processed = f's3://{bucket}/archive/'

    spark \
        .readStream \
        .format('json') \
        .schema(source_schema_tweet) \
        .option('path', source_path) \
        .option('mode', source_mode) \
        .option('maxFilesPerTrigger', source_files) \
        .option('cleanSource', 'archive') \
        .option('sourceArchiveDir', source_processed) \
        .load() \
        .writeStream \
        .foreachBatch(
            lambda df, epoch_id: process(df, epoch_id, args)
        ) \
        .start()

    spark.streams.awaitAnyTermination()

if __name__ == '__main__':
    main(
        getResolvedOptions(sys.argv,[
            'JOB_NAME',
            'BUCKET'
        ])
    )