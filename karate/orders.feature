Feature: Checkout de pedidos (caja negra / API funcional)

  Background:
    * url apiBase
    # Toma un producto real con stock disponible del catálogo sembrado.
    Given path 'products'
    When method get
    Then status 200
    * def conStock = karate.filter(response, function(p){ return p.stock > 0 })
    * assert conStock.length > 0
    * def prod = conStock[0]

  Scenario: Compra como invitado (contra entrega) crea el pedido
    Given path 'orders'
    And request
      """
      {
        "customer_name": "Cliente QA",
        "customer_email": "cliente@karate.test",
        "customer_phone": "3000000000",
        "shipping_address": "Calle 1 # 2-3",
        "payment_method": "contra_entrega",
        "items": [{ "product_id": #(prod.id), "quantity": 1 }]
      }
      """
    When method post
    Then status 201
    And match response.id == '#number'
    And match response.items[0].product_id == prod.id
    And match response.total == '#present'

  Scenario: Stock insuficiente devuelve 409
    Given path 'orders'
    And request
      """
      {
        "customer_name": "Cliente QA",
        "customer_email": "cliente@karate.test",
        "customer_phone": "3000000000",
        "shipping_address": "Calle 1 # 2-3",
        "payment_method": "contra_entrega",
        "items": [{ "product_id": #(prod.id), "quantity": 999999 }]
      }
      """
    When method post
    Then status 409

  Scenario: Producto inexistente devuelve 404
    Given path 'orders'
    And request
      """
      {
        "customer_name": "Cliente QA",
        "customer_email": "cliente@karate.test",
        "customer_phone": "3000000000",
        "shipping_address": "Calle 1 # 2-3",
        "payment_method": "contra_entrega",
        "items": [{ "product_id": 999999, "quantity": 1 }]
      }
      """
    When method post
    Then status 404
