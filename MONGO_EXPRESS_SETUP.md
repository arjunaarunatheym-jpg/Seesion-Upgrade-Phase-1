# Mongo Express Database Admin Setup

## ✅ Status: INSTALLED & RUNNING

Mongo Express is a web-based MongoDB admin interface that allows you to view, edit, and manage your database without writing code.

## 🔐 Access Credentials

- **Username**: `admin`
- **Password**: `mddrc2024`

## 🌐 Access Information

Mongo Express is currently running on **port 8082** inside the container.

### Internal Access (within container)
```bash
curl -u admin:mddrc2024 http://localhost:8082
```

### External Access Options

**✅ Option 1: Through Application URL with /db-admin Path (CONFIGURED)**
I've set up an internal nginx proxy that routes `/db-admin/` to Mongo Express!

**Current Setup:**
- Internal nginx proxy is running on port 8083
- Routes configured:
  - `/db-admin/` → Mongo Express (port 8082)
  - `/api/` → Backend API (port 8001)
  - `/` → Frontend (port 3000)

**To Make It Accessible:**
You'll need to contact the Emergent platform support to update the Kubernetes ingress configuration to route traffic to port 8083 instead of port 3000. Once that's done, you'll be able to access Mongo Express at:

**`https://admin-command-center-16.preview.emergentagent.com/db-admin/`**

Just login with:
- Username: `admin`
- Password: `mddrc2024`

**Option 2: Port Forwarding (Alternative for testing)**
```bash
kubectl port-forward <pod-name> 8083:8083
```
Then access at: `http://localhost:8083/db-admin/`

**Option 3: Direct Mongo Express Port**
```bash
kubectl port-forward <pod-name> 8082:8082
```
Then access at: `http://localhost:8082`

## 📊 Available Databases

Currently connected databases:
- `driving_training_db` - Your main application database
- `admin` - MongoDB admin database
- `config` - MongoDB configuration database  
- `local` - MongoDB local database

## 🛠️ Technical Details

- **Version**: mongo-express 0.54.0
- **MongoDB Connection**: mongodb://localhost:27017
- **Service Manager**: Supervisor
- **Config File**: `/etc/supervisor/conf.d/mongo-express.conf`

## 🔄 Service Management

To check if the service is running:
```bash
sudo supervisorctl status mongo-express
```

To restart the service:
```bash
sudo supervisorctl restart mongo-express
```

To view logs:
```bash
tail -n 50 /var/log/supervisor/mongo-express.out.log
tail -n 50 /var/log/supervisor/mongo-express.err.log
```

## ⚠️ Security Notes

- The current credentials (`admin:mddrc2024`) are set in `/etc/supervisor/conf.d/mongo-express.conf`
- For production environments, ensure proper authentication and access controls are in place
- Consider using IP whitelisting or VPN access for the database admin interface

## 📝 Features Available

Through Mongo Express you can:
- Browse all databases and collections
- View, edit, and delete documents
- Add new documents
- Run queries
- Import/export data
- View database statistics
- Manage indexes

## 🐛 Troubleshooting

If the service is not running:
1. Check supervisor status: `sudo supervisorctl status mongo-express`
2. Check logs for errors: `tail -n 100 /var/log/supervisor/mongo-express.err.log`
3. Verify MongoDB is running: `sudo supervisorctl status mongodb`
4. Restart the service: `sudo supervisorctl restart mongo-express`
