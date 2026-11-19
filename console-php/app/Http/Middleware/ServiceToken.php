<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/** Static bearer token for machine callers (gateway, eval-reporter). Constant-time comparison; fails closed if unset. */
class ServiceToken
{
    public function handle(Request $request, Closure $next): Response
    {
        $expected = (string) config('services.console.service_token');
        $given = (string) $request->bearerToken();

        if ($expected === '' || $given === '' || ! hash_equals($expected, $given)) {
            return response()->json(['message' => 'Unauthenticated.'], 401);
        }

        return $next($request);
    }
}
