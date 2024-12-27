to_rename = [
    ["Iqualuit", "Iqaluit"],
    ["Iqualuit coast", "Iqaluit coast"],
    ["Arkangelsk", "Arkhangelsk"],
    ["Arkangelsk coast", "Arkhangelsk coast"],
    ["Cartogena", "Cartagena"],
    ["Cartogena coast", "Cartagena coast"],
    ["Philippene Sea", "Philippine Sea"]
]

with open("assets/imperial_diplomacy.svg", 'r') as f:
    txt = f.read()

for find, replace in to_rename:
    txt = txt.replace(find, replace)

with open("assets/imperial_diplomacy.svg", 'w') as f:
    f.write(txt)

SQL_format = """
UPDATE {table_name}
SET {column_name} = '{replace}'
WHERE {column_name} = '{search}';
"""

# table_name, column
db_usages = [
    ["provinces", "province_name"],
    ["retreat_options", "origin"],
    ["retreat_options", "retreat_loc"],
    ["units", "location"],
    ["units", "order_source"],
    ["units", "order_destination"],
    ["builds", "location"]
]

SQL_txt = "BEGIN TRANSACTION;"

for table, column in db_usages:
    for find, replace in to_rename:
        SQL_txt += SQL_format.format(table_name=table, column_name=column, replace=replace, search=find)
    
SQL_txt += "\nCOMMIT;\n"

with open("SQL/Rename.out.sql", 'w') as f:
    f.write(SQL_txt)