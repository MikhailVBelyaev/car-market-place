kubectl exec -i deployment/postgres -- \
  psql -U marketplace_user -d postgres -h localhost -p 5432 \
  < backend/dump_duplicate_fix_script.sql