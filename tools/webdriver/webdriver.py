import httplib
import json
import logging
import os
import sys
import urlparse


logging.basicConfig()
logger = logging.getLogger("web-platform-tests")
repo_root = os.path.abspath(os.path.split(__file__)[0])

sys.path.insert(1, os.path.join(repo_root, "tools", "wptserve"))
from wptserve import handlers
from wptserve.router import any_method, Router


def get_desired_capabilities(req, resp):
	try:
		id = req.route_match["session_id"]
		return req.server.sessions[id]
	except KeyError:
		print "Could not find session %s" % id or None
		resp.set_error(404, "No such session")
		resp.write()
		raise


def put_session(req, resp):
	data = json.loads(req.body)
	id, caps = data["sessionId"], data["capabilities"]
	if "-w3c-proxy-endpoint" not in caps:
		resp.set_error(500, "Missing capability -w3c-proxy-endpoint")
	else:
		print "Registering webdriver session %s" % id
		print "New session capabilities: %s" % caps
		req.server.sessions[id] = caps
		return [("Content-Type", "text/plain")], "OK"


def proxy(client_req, client_resp):
	print "entering proxy"

	caps = get_desired_capabilities(client_req, client_resp)
	endpoint = urlparse.urlparse(caps["-w3c-proxy-endpoint"])
	request_path = endpoint.path + client_req.request_path[len("/session"):]
	print "client_req.request_path: %s" % client_req.request_path
	print "client_req.headers: %s" % client_req.headers
	print "endpoint.path: %s" % endpoint.path
	print "request_path: %s" % request_path

	raw_input = client_req.raw_input.read()
	print "client input: %s" % raw_input

	print "Proxying %s %s to %s" % (client_req.method, client_req.request_path,
		"http://%s%s" % (endpoint.netloc, request_path))
	print "%s %s %s" % (client_req.method, endpoint.netloc, request_path)
	server_conn = httplib.HTTPConnection(endpoint.netloc)
	
	headers = {}
	for k,v in client_req.headers.iteritems():
		headers[k] = v
	print "formatted headers: %s" % headers
	
	server_conn.request(client_req.method, request_path,
		raw_input, headers) #client_req.headers)
	server_resp = server_conn.getresponse()
	
	content = server_resp.read()

	#client_resp.writer.write_status(server_resp.status)
	#for h in server_resp.getheaders():
	#	client_resp.writer.write_header(*h)
	#client_resp.writer.end_headers()
	#client_resp.writer.write(content)
	#client_resp.writer.flush()
	
	print "<- %s %s" % (server_resp.status, content)
	
	client_resp.status = server_resp.status
	client_resp.content = content
	
	print "server_resp headers: %s" % server_resp.getheaders()
	for h in server_resp.getheaders():
		client_resp.headers.set(*h)
	print "client_resp headers: %s" % client_resp.headers
	print "client_resp status: %s %s" % client_resp.status
	print "client_resp content: %s" % client_resp.content

	#client_resp.headers = server_resp.getheaders()
	
	print "leaving proxy"
	print ""
	print ""
	print ""


routes = [("POST", "/session", put_session),
	(any_method, "/session/{session_id}*", proxy)]


def session_handler(req, resp):
 	router = Router(repo_root, routes)
	handler = router.get_handler(req)
	print ""
	print ""
	print ""
	if handler is None:
		return handlers.ErrorHandler(404)(req, resp)
	else:
		return handler(req, resp)
