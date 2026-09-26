from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / 'streamlit_app.py')


def run_app():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    return at


def metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_app_renders_report_example():
    at = run_app()
    assert len(at.tabs) == 5
    assert metric(at, 'Orders') == '3'
    assert metric(at, 'Cheapest supplier') == 'Supplier A'
    assert metric(at, 'Cost of forecasted demand') == '₹1,260.00'
    # Greedy is first; both plans serve orders 102 and 101 in this example.
    assert [m.value for m in at.metric if m.label == 'Orders served'] == ['2 / 3', '2 / 3']
    assert [m.value for m in at.metric if m.label == 'Cost'] == ['₹997.50', '₹997.50']


def test_loading_larger_preset_and_changing_budget():
    at = run_app()
    at.sidebar.selectbox[0].select('City hospital (10 items)')
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert metric(at, 'Orders') == '10'
    assert metric(at, 'Cheapest supplier') == 'CarePlus Pharma'

    at.sidebar.number_input(key='budget').set_value(5000.0).run()
    assert not at.exception
    greedy, optimal = [m.value for m in at.metric if m.label == 'Priority served']
    assert int(optimal.split(' / ')[0]) >= int(greedy.split(' / ')[0])


def test_applying_forecasts_updates_orders():
    at = run_app()
    at.radio[0].set_value('Linear trend').run()
    next(b for b in at.button if b.label.startswith('Use linear trend')).click().run()
    assert not at.exception
    assert at.session_state.orders['Forecast'].tolist() != [60, 35, 25]
