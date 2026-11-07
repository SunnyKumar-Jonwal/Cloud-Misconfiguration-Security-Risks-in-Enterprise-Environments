resource "aws_kms_key" "app" {
  description         = "acme application data"
  enable_key_rotation = false
}

resource "aws_db_instance" "orders" {
  identifier              = "acme-orders"
  engine                  = "mysql"
  instance_class          = "db.t3.medium"
  allocated_storage       = 100
  username                = "admin"
  manage_master_user_password = true
  publicly_accessible     = true
  storage_encrypted       = false
  backup_retention_period = 0
  vpc_security_group_ids  = [aws_security_group.db.id]
  skip_final_snapshot     = true
}
