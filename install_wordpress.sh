#!/bin/bash

# Function to prompt for user input with a default value
prompt_input() {
    read -p "$1 [$2]: " input
    echo "${input:-$2}"
}

# Function to generate a random alphanumeric string of specified length
generate_random_string() {
    cat /dev/urandom | tr -dc 'a-z0-9' | fold -w "$1" | head -n 1
}

# Generate a unique WordPress user
wpuser=""
while [ -z "$wpuser" ] || id "$wpuser" &>/dev/null; do
    wpuser=$(generate_random_string 5)
done

# Generate a unique database name (same as dbuser)
dbname=""
while [ -z "$dbname" ] || mysql -u root -pNOR120way -e "USE $dbname" 2>/dev/null; do
    dbname=$(generate_random_string 8 | tr '[:upper:]' '[:lower:]')
done

# Generate a random database password
dbpassword=$(generate_random_string 8)

# Prompt for necessary information
domain=$(prompt_input "Enter the domain for the WordPress site (without 'https://')")
admin_username=$(prompt_input "Enter the admin username")
admin_password=$(prompt_input "Enter the admin password")
admin_email=$(prompt_input "Enter the admin email")

# Create WordPress user and home directory
useradd -m -d /home/${wpuser} -s /bin/bash ${wpuser}

# Set password for the new user (optional)
echo "${wpuser}:${wpuser}" | chpasswd

# Create public_html directory
mkdir /home/${wpuser}/public_html

# Set permissions for public_html directory
chown -R ${wpuser}:${wpuser} /home/${wpuser}/public_html
chmod 755 /home/${wpuser}/public_html

# Update .bashrc file to change to ~/public_html on login
echo "cd ~/public_html" >> /home/${wpuser}/.bashrc

# Create Nginx configuration
nginx_config="/etc/nginx/conf.d/${domain}.conf"
cat > "${nginx_config}" <<EOF
server {
    listen 80;
    server_name ${domain};
    root /home/${wpuser}/public_html;
    index index.php;

    location / {
        try_files \$uri \$uri/ /index.php?\$args;
    }

    location ~ \.php$ {
        try_files \$uri =404;
        fastcgi_pass unix:/run/php-fpm/${wpuser}.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include fastcgi_params;
    }

    location = /favicon.ico {
        log_not_found off;
        access_log off;
    }

    location = /robots.txt {
        allow all;
        log_not_found off;
        access_log off;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico)$ {
        expires max;
        log_not_found off;
    }
}
EOF

# Create PHP-FPM configuration
php_fpm_config="/etc/php-fpm.d/${wpuser}.conf"
cat > "${php_fpm_config}" <<EOF
[${wpuser}]
user = ${wpuser}
group = ${wpuser}
listen = /run/php-fpm/${wpuser}.sock
listen.owner = nginx
listen.group = nginx
listen.mode = 0660
pm = dynamic
pm.max_children = 100
pm.start_servers = 10
pm.min_spare_servers = 5
pm.max_spare_servers = 20
pm.max_requests = 500
pm.status_path = /status
EOF

# Reload Nginx and PHP-FPM
systemctl reload nginx
systemctl restart php-fpm

# Create the database
mysql -u root -pNOR120way -e "CREATE DATABASE ${dbname}; GRANT ALL ON ${dbname}.* TO '${dbname}'@'localhost' IDENTIFIED BY '${dbpassword}'; FLUSH PRIVILEGES;"

# Install WordPress using wp-cli
cd /home/${wpuser}/public_html
/usr/local/bin/wp core download
/usr/local/bin/wp core config --dbname=${dbname} --dbuser=${dbname} --dbpass=${dbpassword} --dbhost=localhost --dbprefix=wp_
/usr/local/bin/wp core install --url="https://${domain}" --title="My WordPress Site" --admin_user=${admin_username} --admin_password=${admin_password} --admin_email=${admin_email}

# Set ownership and permissions for /home/{wpuser} directory and its contents
chown -R ${wpuser}:${wpuser} /home/${wpuser}
chmod +rx /home/${wpuser}

# Fix SELinux permissions
chcon -R -t httpd_sys_content_t /home/${wpuser}/public_html/

# Apply ownership of PHP-FPM pool socket to Nginx
chown nginx:nginx /run/php-fpm/${wpuser}.sock

echo "WordPress installation completed successfully."
