<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/** Usage: ->middleware('role:admin') or 'role:admin,viewer'. 401 if unauthenticated, 403 if role not allowed. */
class EnsureRole
{
    public function handle(Request $request, Closure $next, string ...$roles): Response
    {
        $user = $request->user();
        if (! $user) {
            abort(401, 'Unauthenticated.');
        }
        if (! in_array($user->role, $roles, true)) {
            abort(403, 'Forbidden.');
        }

        return $next($request);
    }
}
