import asyncio
import os
import requests
import psycopg2

from ...provider import BaseProvider

POSTGRES_USER = os.environ.get("POSTGRES_USER", "synapse")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "synapse")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "db")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", 5432)


class SynapseProvider(BaseProvider):
    def update_routes(self, routes):
        dest_to_costs = {}

        result = ''
        result += self.run(["./scripts/clear_hs_routes.sh"])
        for route in routes:
            server_id = route['dst']['id']
            hostname = f"meshsim-node{server_id}"

            dest_to_costs[hostname] = route["cost"]

            if route['via'] is None:
                continue

            result += self.run([
                "./scripts/add_hs_route.sh", route['dst']['ip'], route['via']['ip'],
            ])

        self.write_destination_health(dest_to_costs)

        return result

    def write_destination_health(self, dest_to_costs):
        conn = psycopg2.connect(
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
        with conn:
            with conn.cursor() as txn:
                txn.execute("TRUNCATE destination_health")
                for destination, cost in dest_to_costs.items():
                    txn.execute(
                        "INSERT INTO destination_health VALUES (%s, %s)",
                        (destination, cost),
                    )

        try:
            requests.get(
                "http://localhost:8008/_matrix/client/r0/admin/server_health")
        except Exception as e:
            pass
