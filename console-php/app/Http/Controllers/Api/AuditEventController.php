<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\AuditEvent;
use Illuminate\Http\Request;

class AuditEventController extends Controller
{
    use Paginates;

    public function index(Request $request)
    {
        $request->validate(['type' => ['sometimes', 'in:'.implode(',', AuditEvent::TYPES)]]);
        $q = AuditEvent::query();
        if ($request->filled('type')) {
            $q->where('type', $request->query('type'));
        }

        return $this->paginated($q, $request);
    }

    public function store(Request $request)
    {
        $data = $request->validate([
            'type' => ['required', 'in:'.implode(',', AuditEvent::TYPES)],
            'actor' => ['required', 'string', 'max:255'],
            'subject' => ['sometimes', 'nullable', 'string', 'max:255'],
            'detail' => ['sometimes', 'nullable', 'array'],
        ]);

        return response()->json(AuditEvent::create($data)->refresh(), 201);
    }
}
