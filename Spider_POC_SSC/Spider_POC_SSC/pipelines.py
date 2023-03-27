# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from google.cloud import bigquery
import time
import logging


class BigQueryPipeline:

    def __init__(self, project_id, dataset_id, table_id):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = table_id

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            project_id=crawler.settings.get('GCP_PROJECT_ID'),
            dataset_id=crawler.settings.get('BQ_DATASET_ID'),
            table_id=crawler.settings.get('BQ_TABLE_ID')
        )

    def open_spider(self, spider):
        self.client = bigquery.Client(project=self.project_id)

        # Create dataset if not exists
        dataset_ref = self.client.dataset(self.dataset_id)
        try:
            dataset = bigquery.Dataset(dataset_ref)
            self.client.create_dataset(dataset)
            logging.info(f"Create dataset {dataset_ref}")
        except Exception as e:
            self.client.get_dataset(dataset_ref)  
            logging.info(f"Dataset {dataset_ref} already exist")

        # Create table if not exists
        self.table_ref = dataset_ref.table(spider.bq_table_name)

        if spider.bq_table_name.startswith('company_info_'):
            try:
                schema = [
                    bigquery.SchemaField("COMPANY_NAME", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("COMPANY_MDN", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("COMPANY_GENERAL_INFO", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("COMPANY_NNB_NNQ_SHAREHOLDERS_DATA", "STRING", mode="NULLABLE")
                ]
                table = bigquery.Table(self.table_ref, schema = schema)
                self.client.create_table(table)
                logging.info(f"Create table {self.table_ref}")
            # 如果x以'tax_num_'为前缀，则执行以下代码
            except Exception as e:
                time.sleep(5)
                logging.info(f"Table {self.table_ref} already exist")

        elif spider.bq_table_name.startswith('company_finance_'):
            try:
                schema = [
                    bigquery.SchemaField("COMPANY_NAME", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("COMPANY_MDN", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("REPORT_NAME", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("REPORT_BCDKT", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("REPORT_KQKD", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("REPORT_LCTT_TT", "STRING", mode="NULLABLE"),
                    bigquery.SchemaField("REPORT_LCTT_GT", "STRING", mode="NULLABLE")
                ]
                table = bigquery.Table(self.table_ref, schema = schema)
                self.client.create_table(table)
                logging.info(f"Create table {self.table_ref}")
            except Exception as e:
                time.sleep(5)
                logging.info(f"Table {self.table_ref} already exist")
                
    def process_item(self, item, spider):
        item_data = dict(item)
        errors = self.client.insert_rows_json(self.table_ref, [item_data])
        if errors:
            logging.error(f"Errors while streaming data to BigQuery: {errors}")

        return item

class SpiderPocGdtPipeline:
    def process_item(self, item, spider):
        return item
