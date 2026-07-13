const https = require("https");
const { Client } = require("pg");
const crypto = require("crypto");

const ORDER_ID = "jY3r4cKIXHg6tnsi";
const INBOUND_ID = "solyra-inbound-wa01";
const BASE =
  "https://raw.githubusercontent.com/itsmebtmg/Backend/main/docs/n8n";

function fetchJson(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => resolve(JSON.parse(data)));
      })
      .on("error", reject);
  });
}

async function upsertWorkflow(client, id, wf, active) {
  const versionId = crypto.randomUUID();
  await client.query(
    `INSERT INTO workflow_entity
      (id, name, active, nodes, connections, settings, "versionId", "triggerCount",
       "createdAt", "updatedAt", "isArchived", "versionCounter")
     VALUES ($1,$2,$3,$4::json,$5::json,$6::json,$7,1,NOW(),NOW(),false,1)
     ON CONFLICT (id) DO UPDATE SET
       name = EXCLUDED.name,
       active = EXCLUDED.active,
       nodes = EXCLUDED.nodes,
       connections = EXCLUDED.connections,
       settings = EXCLUDED.settings,
       "updatedAt" = NOW()`,
    [
      id,
      wf.name,
      active,
      JSON.stringify(wf.nodes),
      JSON.stringify(wf.connections),
      JSON.stringify(wf.settings || { executionOrder: "v1" }),
      versionId,
    ],
  );
}

async function main() {
  const order = await fetchJson(`${BASE}/solyra-order-to-whatsapp.json`);
  const inbound = await fetchJson(`${BASE}/solyra-whatsapp-inbound.json`);

  const client = new Client({
    host: process.env.DB_POSTGRESDB_HOST,
    port: Number(process.env.DB_POSTGRESDB_PORT || 5432),
    database: process.env.DB_POSTGRESDB_DATABASE,
    user: process.env.DB_POSTGRESDB_USER,
    password: process.env.DB_POSTGRESDB_PASSWORD,
  });
  await client.connect();

  await upsertWorkflow(client, ORDER_ID, order, true);
  await upsertWorkflow(client, INBOUND_ID, inbound, true);

  const { rows } = await client.query(
    "SELECT id, name, active FROM workflow_entity ORDER BY name",
  );
  console.log(JSON.stringify(rows, null, 2));
  await client.end();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
