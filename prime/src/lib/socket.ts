/**
 * Socket.io connection to the Frappe realtime server.
 *
 * Vendored from doppio because its version hardcodes port 9000 whenever a port
 * is present in the URL. This bench runs socketio on 9002, so the original
 * never connected. The port now comes from the server, via the boot payload
 * that `www/shop.py` renders into the page.
 *
 * Not used yet. The live-order feed on the admin dashboard is the first
 * consumer; this exists so that feature is a small change rather than a
 * debugging session.
 */

import { io, type Socket } from 'socket.io-client';
import { boot } from './boot';

let socket: Socket | null = null;

export function getSocket(): Socket {
	if (socket) return socket;

	const host = window.location.hostname;
	const port = boot.socketio_port;

	// In production the realtime server sits behind the same origin and is
	// proxied at /socket.io. In development it listens on its own port.
	const url = port ? `${window.location.protocol}//${host}:${port}` : window.location.origin;

	socket = io(url, {
		withCredentials: true,
		reconnectionAttempts: 5
	});

	return socket;
}

export default getSocket;
