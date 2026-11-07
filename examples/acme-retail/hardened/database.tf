resource "aws_kms_key" "app" {
  description         = "acme application data"
  enable_key_rotation = true
}

resource "aws_db_subnet_group" "orders" {
  name       = "acme-orders"
  subnet_ids = [aws_subnet.private.id]
}

resource "aws_db_instance" "orders" {
  identifier                  = "acme-orders"
  engine                      = "mysql"
  instance_class              = "db.t3.medium"
  allocated_storage           = 100
  username                    = "admin"
  manage_master_user_password = true
  publicly_accessible         = false
  storage_encrypted           = true
  kms_key_id                  = aws_kms_key.app.arn
  backup_retention_period     = 14
  deletion_protection         = true
  db_subnet_group_name        = aws_db_subnet_group.orders.name
  vpc_security_group_ids      = [aws_security_group.db.id]
}
