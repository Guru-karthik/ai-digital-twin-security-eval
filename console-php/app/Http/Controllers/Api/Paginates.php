<?php

namespace App\Http\Controllers\Api;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

trait Paginates
{
    /** Returns the OpenAPI Pagination envelope: {page, per_page, total, data}. */
    protected function paginated(Builder $query, Request $request): JsonResponse
    {
        $request->validate([
            'page' => ['sometimes', 'integer', 'min:1'],
            'per_page' => ['sometimes', 'integer', 'min:1', 'max:100'],
        ]);
        $p = $query->orderByDesc('id')->paginate((int) $request->query('per_page', 20));

        return response()->json([
            'page' => $p->currentPage(),
            'per_page' => $p->perPage(),
            'total' => $p->total(),
            'data' => $p->items(),
        ]);
    }
}
