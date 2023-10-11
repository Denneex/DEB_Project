project_id = "lexical-drake-399716"
region   = "us-central1"
location = "us-central1-c"


#GKE
gke_num_nodes = 2
machine_type  = "n1-standard-2"

#CloudSQL
instance_name     = "deb-postgre-db"
database_version  = "POSTGRES_15"
instance_tier     = "db-f1-micro"
disk_space        = 10
database_name     = "postgreDB"
db_username       = "denneex"
db_password       = "wiseline"


