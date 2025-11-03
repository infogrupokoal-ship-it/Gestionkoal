def test_dashboard_kpis(client, auth):
    auth.login()
    response = client.get("/")
    assert response.status_code == 200

    # Check total tickets
    assert (
        b'<div class="stat-number">5</div>\n            <div>Total Trabajos</div>'
        in response.data
    )

    # Check pending tickets (estado = 'abierto')
    assert (
        b'<div class="stat-number">3</div>\n            <div>Trabajos Pendientes</div>'
        in response.data
    )

    # Check pending payments (estado_pago != 'Pagado')
    assert (
        b'<div class="stat-number">3</div>\n            <div>Pagos Pendientes</div>'
        in response.data
    )

    # Check total clients
    assert (
        b'<div class="stat-number">2</div>\n            <div>Total Clientes</div>'
        in response.data
    )

    # Check recent tickets table (example for one ticket)
    assert b"<td>Reparaci\xc3\xb3n A</td>" in response.data
    assert b"<td>Cliente Test 1</td>" in response.data
    assert b"<td>abierto</td>" in response.data
