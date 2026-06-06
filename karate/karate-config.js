/**
 * Configuración global de Karate (caja negra contra la API ya desplegada).
 * baseUrl se inyecta con -DbaseUrl=... (por defecto el preprod local en :8000).
 */
function fn() {
  var baseUrl = karate.properties['baseUrl'] || 'http://localhost:8000';
  var config = {
    baseUrl: baseUrl,
    apiBase: baseUrl + '/api/v1',
  };
  karate.configure('connectTimeout', 10000);
  karate.configure('readTimeout', 20000);
  return config;
}
