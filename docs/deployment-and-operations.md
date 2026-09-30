# Deployment & Operations

## Environment Context
The ZConnect platform is designed to be deployed on a standard Odoo 19 Enterprise stack.

### Recommended Production Topology
1. **Reverse Proxy (Nginx/HAProxy)**: Handles SSL termination, rate limiting, and forwards traffic to Odoo workers.
2. **Odoo Web Workers**: 2-4 Python processes handling standard HTTP traffic and QWeb rendering.
3. **Odoo Gevent Worker**: 1 dedicated worker for long-polling/LiveChat/real-time updates.
4. **PostgreSQL 16**: The core relational database. (PostGIS extension optional but recommended for future spatial queries).
5. **Redis/Memcached (Optional)**: For session management if scaling beyond a single Odoo node.

## Starting the Server
During development and staging on the `OdooDeploymentEngine`, the server is run via a detached startup script:

```powershell
& "C:\Program Files\OdooDeploymentEngine\venv\Scripts\python.exe" "C:\Program Files\OdooDeploymentEngine\start_detached_8070.py"
```

In standard Linux production environments, Odoo should be managed via `systemd`.

## Module Updates
Whenever a Python model (`.py`) or XML view (`.xml`) is changed in the repository, the module must be upgraded to push changes to the database:

```bash
python odoo-bin -c /path/to/odoo.conf -d <database_name> -u zconnect_portal --stop-after-init
```

*Note: The Odoo server must be restarted after Python file changes. XML changes only require a module upgrade (`-u`).*

## Backups
- **Database**: Automated `pg_dump` jobs should be scheduled nightly.
- **Filestore**: The Odoo filestore (which contains the Proof of Delivery signature images and photos) must be backed up concurrently with the database to prevent orphaned attachments.

## Monitoring
Monitor the `odoo-enterprise.log` for:
- `werkzeug` HTTP 500 errors (indicates unhandled API exceptions).
- `odoo.modules.loading` errors (indicates missing dependencies during upgrades).
