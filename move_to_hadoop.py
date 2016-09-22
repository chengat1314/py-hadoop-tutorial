import ibis
import os
import pandas as pd


ibis.options.sql.default_limit = None

hdfs_conn = ibis.hdfs_connect(host='bottou03.sjc.cloudera.com')

ibis_conn = ibis.impala.connect(host='bottou01.sjc.cloudera.com',
                                port=21050,
                                hdfs_client=hdfs_conn)

FILE_SCHEMA = ibis.schema([('project_name', 'string'),
                           ('page_name', 'string'),
                           ('monthly_total', 'int64'),
                           ('hourly_total', 'int64')])

# System independent way to join paths
LOCAL_DATA_PATH = os.path.join(os.getcwd(), "pageviews-gz")
LOCAL_FILES = os.listdir(LOCAL_DATA_PATH)
HDFS_DIR='/user/juliet/pageviews-gz'
DB_NAME='u_juliet'


def mv_files(filename):
    dir_name = HDFS_DIR + filename[:-3]
    hdfs_conn.mkdir(dir_name)
    filepathtarget = '/'.join([dir_name, filename])
    hdfs_conn.put(filepathtarget, os.path.join(LOCAL_DATA_PATH, filename))
    return dir_name


def extract_datetime(filename):
    _, date_str, time_str = filename.split("-")
    year = date_str[:4]
    month = date_str[4:6]
    day = date_str[-2:]
    hour = time_str[:2]
    return year, month, day, hour


def to_pd_dt(filename):
    return pd.to_datetime(filename, format='pageviews-%Y%m%d-%H0000')


def gz_2_data_insert(data_dir):
    tmp_table = ibis_conn.delimited_file(hdfs_dir=data_dir,
                                  schema=FILE_SCHEMA,
                                  delimiter=' ')
    year, month, day, hour = extract_datetime(data_dir.split("/")[-1])
    # create a column named time
    tmp_w_time = tmp_table.mutate(year=year, month=month, day=day, hour=hour)

    working_db = safe_get_db(DB_NAME)
    if 'wiki_pageviews' in working_db.tables:
        ibis_conn.insert('wiki_pageviews', tmp_w_time, database=DB_NAME)
    else:
        ibis_conn.create_table('wiki_pageviews', obj=tmp_w_time,
                               database=DB_NAME)

def safe_get_db(db_name):
    if ibis_conn.exists_database(db_name):
        user_db = ibis_conn.database(db_name)
    else:
        user_db = ibis_conn.create_database(db_name)
    return user_db


def main():
    hdfs_gz_dirs = [mv_files(filename) for filename in LOCAL_FILES]
    [gz_2_data_insert(data_dir) for data_dir in hdfs_gz_dirs]


if __name__ == "__main__":
    main()
