Here’s how you can turn your Excel-based data dictionary into a properly structured JSON file suitable for registering a table in the AWS Glue Data Catalog using the CLI. Since you don’t yet have a Glue Catalog entry for inventory, this will guide you through creating one with both table-level and column-level parameters.

Step 1: Define Your Data Dictionary Format

Based on your Excel, each row contains:

TABLE NAME

COLUMN NAME (possibly with PK notation like id(PK))

DATA TYPE

COLUMN DESCRIPTION

UNIQUE VALUES IN THE COLUMN

USAGE OF THE COLUMN

You'll convert that into a structured JSON TableInput that AWS Glue CLI can consume.

Step 2: Create table_input.json

Here’s an example template. Be sure to preserve critical Glue properties like StorageDescriptor, even if you're only updating schema and metadata.

{
  "Name": "inventory",
  "Description": "Inventory table derived from Excel data dictionary",
  "StorageDescriptor": {
    "Columns": [
      {
        "Name": "id",
        "Type": "string",
        "Comment": "Unique identifier for each inventory record.",
        "Parameters": {
          "unique_values": "e.g.6286220,6286224 etc",
          "usage": "Used as primary key"
        }
      },
      {
        "Name": "cost",
        "Type": "double",
        "Comment": "Cost of the item in inventory.",
        "Parameters": {
          "unique_values": "N/A",
          "usage": "Used for cost analysis"
        }
      },
      {
        "Name": "user",
        "Type": "string",
        "Comment": "User associated with the inventory item.",
        "Parameters": {
          "unique_values": "empty column",
          "usage": "Indicates the user who handled the inventory"
        }
      }
    ],
    "Location": "s3://your-bucket/inventory/",               // Your actual data location
    "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
    "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
    "SerdeInfo": {
      "SerializationLibrary": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
      "Parameters": { "serialization.format": "1" }
    }
  },
  "PartitionKeys": [],
  "TableType": "EXTERNAL_TABLE",
  "Parameters": {
    "relationships": "{\"relationships\":[{\"relationship_name\":\"inventory_user_fk\",\"description\":\"Each inventory record references a user\",\"from_table\":\"inventory\",\"from_column\":\"user\",\"to_table\":\"users\",\"to_column\":\"user_id\",\"relationship_type\":\"many-to-one\"}]}"
  }
}


Notes:

Replace "Location", "InputFormat", SerdeInfo, etc., to match your actual data setup.

Column-level Parameters embed metadata like unique values and usage.

Table-level Parameters include relationships, as a JSON string.

Step 3: Execute via AWS CLI

Run the following command to apply the new table definition:

aws glue create-table \
  --database-name your_database \
  --table-input file://table_input.json


This creates a new Glue table named inventory under the database your_database, with all the schema and metadata you defined.

Step 4: Verification

To confirm everything is registered correctly:

aws glue get-table --database-name your_database --name inventory


View the output under:

Table.StorageDescriptor.Columns[].Parameters — for your column-level metadata

Table.Parameters — for table-level metadata (like relationships)

Summary Table
Step	Description
1. Prepare JSON (table_input.json)	Convert Excel rows into structured Columns and metadata in Parameters.
2. Run CLI create-table	aws glue create-table --table-input file://table_input.json
3. Validate via get-table	Verify the schema and metadata are properly registered.

If you'd like, I can help tailor the JSON further based on additional columns or nuances in your data dictionary. Just let me know!

You need GPT-5 to continue this chat because there's an attachment. Your limit resets after 3:08 PM.
New chat
Upgrade your plan

Search
ChatGPT can make mistakes. Check important info. See Cookie Preferences
