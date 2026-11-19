<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use App\Models\AuditEvent;
use App\Models\Conversation;
use App\Models\EvaluationRun;
use App\Models\Lead;
use Illuminate\Http\Request;

class DashboardController extends Controller
{
    public function leads(Request $request)
    {
        $status = in_array($request->query('status'), Lead::STATUSES, true) ? $request->query('status') : null;
        $leads = Lead::query()->when($status, fn ($q) => $q->where('status', $status))
            ->orderByDesc('id')->simplePaginate(20)->withQueryString();

        return view('dashboard.leads', compact('leads', 'status'));
    }

    public function reviewLead(Request $request, Lead $lead)
    {
        $data = $request->validate(['status' => ['required', 'in:approved,rejected']]);
        $lead->review($data['status'], $request->user());

        return back()->with('status', "Lead #{$lead->id} {$data['status']}.");
    }

    public function conversations()
    {
        $conversations = Conversation::query()
            ->select(['id', 'external_id', 'defense', 'model', 'message_count', 'created_at'])
            ->orderByDesc('id')->simplePaginate(20);

        return view('dashboard.conversations', compact('conversations'));
    }

    public function conversation(Conversation $conversation)
    {
        return view('dashboard.conversation', compact('conversation'));
    }

    public function runs()
    {
        return view('dashboard.runs', ['runs' => EvaluationRun::query()->orderByDesc('id')->simplePaginate(20)]);
    }

    public function audit()
    {
        return view('dashboard.audit', ['events' => AuditEvent::query()->orderByDesc('id')->simplePaginate(20)]);
    }
}
