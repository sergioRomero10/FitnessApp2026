// Se ejecuta UNA sola vez, cuando el volumen de MongoDB está vacío.
// Crea un usuario que solo puede leer/escribir la base de datos de la app,
// en lugar de que la app se conecte con el usuario root.
db = db.getSiblingDB(process.env.MONGO_APP_DB || "fitnessapp");

db.createUser({
  user: process.env.MONGO_APP_USER,
  pwd: process.env.MONGO_APP_PASSWORD,
  roles: [{ role: "readWrite", db: db.getName() }],
});
