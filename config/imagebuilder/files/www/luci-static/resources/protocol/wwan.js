'use strict';
'require baseclass';

/*
 * Placeholder for the "wwan" protocol handler.
 *
 * ImmortalWrt 25.12 (and OpenWrt) do not ship a luci-proto-wwan package any
 * more, but some cached LuCI pages still request
 * /luci-static/resources/protocol/wwan.js. Serving this module keeps that
 * request at 200 instead of a 404; it deliberately registers nothing.
 */
return baseclass.extend({});
