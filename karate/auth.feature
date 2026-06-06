Feature: Autenticación (caja negra / API funcional)

  Background:
    * url apiBase

  Scenario: Registro, login y consulta de perfil
    * def email = 'qa_' + java.lang.System.currentTimeMillis() + '@karate.test'

    Given path 'auth', 'register'
    And request { email: '#(email)', password: 'Secret123!', full_name: 'QA Karate' }
    When method post
    Then status 201
    And match response.email == email
    And match response.role == 'cliente'

    Given path 'auth', 'login'
    And form field username = email
    And form field password = 'Secret123!'
    When method post
    Then status 200
    And match response.access_token == '#string'
    * def token = response.access_token

    Given path 'auth', 'me'
    And header Authorization = 'Bearer ' + token
    When method get
    Then status 200
    And match response.email == email

  Scenario: Login con credenciales inválidas devuelve 401
    Given path 'auth', 'login'
    And form field username = 'inexistente@karate.test'
    And form field password = 'ClaveErronea1'
    When method post
    Then status 401

  Scenario: Email duplicado en registro devuelve 409
    * def email = 'dup_' + java.lang.System.currentTimeMillis() + '@karate.test'
    Given path 'auth', 'register'
    And request { email: '#(email)', password: 'Secret123!', full_name: 'Duplicado' }
    When method post
    Then status 201

    Given path 'auth', 'register'
    And request { email: '#(email)', password: 'Secret123!', full_name: 'Duplicado' }
    When method post
    Then status 409
