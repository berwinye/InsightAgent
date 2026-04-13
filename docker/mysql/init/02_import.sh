#!/bin/bash
set -e

echo "==> Importing classicmodels data into enterprise_api..."

if [ ! -f /tmp/classicmodels.sql ]; then
    echo "ERROR: /tmp/classicmodels.sql not found. Make sure classicmodels.sql is mounted."
    exit 1
fi

# Replace database name 'classicmodels' with 'enterprise_api' and import
sed "s/\`classicmodels\`/\`enterprise_api\`/g" /tmp/classicmodels.sql | \
    mysql -u root -p"${MYSQL_ROOT_PASSWORD}"

echo "==> classicmodels data imported successfully."
