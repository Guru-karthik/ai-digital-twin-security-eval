<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Lead;
use Illuminate\Http\Request;

class LeadController extends Controller
{
    use Paginates;

    public function index(Request $request)
    {
        $request->validate(['status' => ['sometimes', 'in:'.implode(',', Lead::STATUSES)]]);
        $q = Lead::query();
        if ($request->filled('status')) {
            $q->where('status', $request->query('status'));
        }

        return $this->paginated($q, $request);
    }

    public function show(Lead $lead)
    {
        return $lead;
    }

    public function store(Request $request)
    {
        $data = $request->validate([
            'email' => ['required', 'email', 'max:254'],
            'name' => ['sometimes', 'nullable', 'string', 'max:200'],
            'notes' => ['sometimes', 'nullable', 'string', 'max:2000'],
            'conversation_id' => ['sometimes', 'nullable', 'string', 'max:255'],
        ]);

        return response()->json(Lead::create($data)->refresh(), 201);
    }

    /** Admin approve/reject. This is a console feature, not agent-side human-in-the-loop. */
    public function update(Request $request, Lead $lead)
    {
        $data = $request->validate(['status' => ['required', 'in:approved,rejected']]);

        $lead->review($data['status'], $request->user());

        return $lead;
    }
}
