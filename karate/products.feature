Feature: Catálogo de productos (caja negra / API funcional)

  Background:
    * url apiBase

  Scenario: Listar el catálogo devuelve al menos un producto
    Given path 'products'
    When method get
    Then status 200
    And match response == '#array'
    And assert response.length > 0

  Scenario: Detalle de producto existente y 404 para inexistente
    Given path 'products'
    When method get
    Then status 200
    * def first = response[0]

    Given path 'products', first.id
    When method get
    Then status 200
    And match response.id == first.id
    And match response.name == '#string'
    And match response.price == '#present'

    Given path 'products', 999999
    When method get
    Then status 404

  Scenario: Filtro por categoría devuelve solo esa categoría
    Given path 'products'
    When method get
    Then status 200
    * def cat = response[0].category

    Given path 'products'
    And param category = cat
    When method get
    Then status 200
    And match each response contains { category: '#(cat)' }

  Scenario: Crear producto sin autenticación está prohibido
    Given path 'products'
    And request { name: 'No autorizado', price: 1000, stock: 1 }
    When method post
    Then status 401
