import type { IncomingMessage } from 'node:http';

import common_site_config from '../../../sites/common_site_config.json' with { type: 'json' };

const { webserver_port } = common_site_config;

// Dev-server proxy. `yarn dev` serves the SPA on :8080 and forwards every
// Frappe path to the bench webserver, so API calls, assets and uploads behave
// exactly as they will in production.
export default {
	'^/(app|api|assets|files|private)': {
		target: `http://127.0.0.1:${webserver_port}`,
		ws: true,
		router(req: IncomingMessage) {
			const hostname = req.headers.host?.split(':')[0];
			return `http://${hostname}:${webserver_port}`;
		}
	}
};
