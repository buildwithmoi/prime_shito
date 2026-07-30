/**
 * Frappe API client.
 *
 * Vendored from doppio rather than imported, for three reasons:
 *
 *  1. doppio is not in this site's installed_apps. The old
 *     `../../../doppio/libs/...` imports only resolved because a sibling
 *     directory happened to exist in this bench, so any clean checkout or CI
 *     runner without doppio failed to build.
 *  2. doppio's version redirects to /login on any 401/403. Its guard reads
 *     `router.currentRoute.name`, but on vue-router 4 `currentRoute` is a Ref,
 *     so `.name` is always undefined and the guard never fires. On a public
 *     storefront that bounced shoppers to a dead route on any permission error.
 *     This version throws instead and lets the caller decide.
 *  3. Adds a request timeout, which the original had no way to express.
 */

export interface FrappeErrorShape {
	exc_type?: string;
	exc?: string;
	_error_message?: string;
	_server_messages?: string;
	message?: string;
}

export class FrappeError extends Error {
	status: number;
	excType?: string;
	messages: string[];

	constructor(message: string, status: number, messages: string[], excType?: string) {
		super(message);
		this.name = 'FrappeError';
		this.status = status;
		this.messages = messages;
		this.excType = excType;
	}
}

const DEFAULT_TIMEOUT_MS = 20_000;

function parseServerMessages(raw?: string): string[] {
	if (!raw) return [];
	try {
		const parsed = JSON.parse(raw) as string[];
		return parsed
			.map((entry) => {
				try {
					return JSON.parse(entry).message as string;
				} catch {
					return entry;
				}
			})
			.filter(Boolean);
	} catch {
		return [];
	}
}

function stripHtml(value: string): string {
	// Frappe error messages routinely carry <br> and <b>. The UI renders them
	// as plain text, so flatten rather than trusting the markup.
	return value
		.replace(/<br\s*\/?>/gi, '\n')
		.replace(/<[^>]+>/g, '')
		.trim();
}

export interface CallOptions {
	timeout?: number;
	signal?: AbortSignal;
	method?: 'GET' | 'POST';
}

export default async function call<T = any>(
	method: string,
	args: Record<string, unknown> = {},
	options: CallOptions = {}
): Promise<T> {
	const { timeout = DEFAULT_TIMEOUT_MS, signal } = options;

	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), timeout);
	if (signal) {
		signal.addEventListener('abort', () => controller.abort(), { once: true });
	}

	const headers: Record<string, string> = {
		Accept: 'application/json',
		'Content-Type': 'application/json; charset=utf-8',
		'X-Frappe-Site-Name': window.location.hostname
	};

	// Guests carry no persisted CSRF token in Frappe, so this is a no-op for
	// shoppers. It matters when a logged-in staff member uses the storefront.
	const csrf = (window as any).csrf_token;
	if (csrf && csrf !== '{{ csrf_token }}') {
		headers['X-Frappe-CSRF-Token'] = csrf;
	}

	let response: Response;
	try {
		response = await fetch(`/api/method/${method}`, {
			method: 'POST',
			headers,
			body: JSON.stringify(args),
			signal: controller.signal
		});
	} catch (err) {
		clearTimeout(timer);
		if ((err as Error).name === 'AbortError') {
			throw new FrappeError(
				'That took too long. Please check your connection and try again.',
				0,
				['Request timed out']
			);
		}
		throw new FrappeError(
			'We could not reach the server. Please check your connection.',
			0,
			['Network error']
		);
	}
	clearTimeout(timer);

	const text = await response.text();

	if (response.ok) {
		if (!text) return undefined as T;
		const data = JSON.parse(text);
		// `login` and doc-returning endpoints use a different envelope.
		if (data.docs || method === 'login') return data as T;
		return data.message as T;
	}

	let payload: FrappeErrorShape = {};
	try {
		payload = JSON.parse(text);
	} catch {
		/* non-JSON error body, e.g. an HTML 502 page */
	}

	const messages = [
		...parseServerMessages(payload._server_messages),
		payload._error_message,
		payload.message
	]
		.filter((m): m is string => Boolean(m))
		.map(stripHtml)
		.filter(Boolean);

	if (!messages.length) {
		messages.push(
			response.status === 429
				? 'You are going a bit fast. Please wait a moment and try again.'
				: 'Something went wrong. Please try again.'
		);
	}

	throw new FrappeError(messages[0], response.status, messages, payload.exc_type);
}
