# server.py - Flask server to receive WayForPay callbacks (recToken etc.)
from flask import Flask, request, jsonify
import config, db_utils, json, logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/wfp-callback', methods=['POST'])
def wfp_callback():
    try:
        payload = request.json if request.is_json else request.form.to_dict()
    except Exception:
        payload = request.form.to_dict()
    app.logger.info("WFP callback payload: %s", payload)

    order_ref = payload.get('orderReference') or payload.get('order_reference')
    uid = None
    if order_ref and order_ref.startswith('sub_'):
        parts = order_ref.split('_')
        if len(parts) >= 3:
            uid = parts[1]
    recToken = payload.get('recToken') or payload.get('rec_token')
    status = payload.get('transactionStatus') or payload.get('orderStatus') or payload.get('transaction_status')

    if uid and status and str(status).lower() in ('approved','success','settled'):
        db_utils.mark_paid(uid, months=1, recToken=recToken)
        app.logger.info("Marked paid for user %s recToken=%s", uid, recToken)
    else:
        app.logger.info("Callback received but not marked paid. order_ref=%s status=%s", order_ref, status)

    return jsonify({'status':'accept', 'orderReference': order_ref})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
