import httplib
import json
import os
import sys
import urlparse


repo_root = os.path.abspath(os.path.split(__file__)[0])

sys.path.insert(1, os.path.join(repo_root, "tools", "wptserve"))
from wptserve import handlers
from wptserve.router import any_method, Router


def get_desired_capabilities(req, resp):
	try:
		id = req.route_match["session_id"]
		return req.server.sessions[id]
	except KeyError:
		resp.set_error(404, "No such session")
		resp.write()
		raise


def put_session(req, resp):
	data = json.loads(req.body)
	id, caps = data["sessionId"], data["capabilities"]
	if "-w3c-proxy-endpoint" not in caps:
		resp.set_error(500, "Missing capability -w3c-proxy-endpoint")
	else:
		req.server.sessions[id] = caps
		return [("Content-Type", "text/plain")], "OK"


def proxy(client_req, client_resp):
	caps = get_desired_capabilities(client_req, client_resp)
	endpoint = urlparse.urlparse(caps["-w3c-proxy-endpoint"])

	server_conn = httplib.HTTPConnection(endpoint.netloc)
	server_conn.request(client_req.method, client_req.request_path, client_req.raw_input, client_req.headers)
	server_resp = server_conn.getresponse()

	client_resp.writer.write_status(server_resp.status)
	for h in server_resp.getheaders():
		client_resp.writer.write_header(*h)
	client_resp.writer.end_headers()
	client_resp.writer.write(server_resp.read())


routes = [("POST", "/session", put_session),
	(any_method, "/session/{session_id}*", proxy)]


def session_handler(req, resp):
 	router = Router(repo_root, routes)
	handler = router.get_handler(req)
	if handler is None:
		return handlers.ErrorHandler(404)(req, resp)
	else:
		return handler(req, resp)
