from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

sc = SparkContext()
glueContext = GlueContext(sc)
job = Job(glueContext)
spark = glueContext.spark_session

# Jobs Arguments
args = getResolvedOptions(sys.argv,[
    'JOB_NAME'
])
job_name = args['JOB_NAME']

# Start
print('START')
job.init(job_name,args)

spark.sql('show databases')

# End
print('END')
job.commit()