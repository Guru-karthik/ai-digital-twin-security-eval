<?php

namespace App\Http\Controllers;

use App\Models\AuditEvent;
use App\Models\Conversation;
use App\Models\EvaluationRun;
use App\Models\Lead;
use Illuminate\Http\Request;

/** Prometheus text exposition built from table counts. Stateless: no extra storage or packages. */
class MetricsController extends Controller
{
    public function __invoke(Request $request)
    {
        $expected = (string) config('services.console.metrics_token');
        // Disabled (404) when no token is configured; 401 for a wrong token. Constant-time comparison.
        abort_if($expected === '', 404);
        abort_unless(hash_equals($expected, (string) $request->bearerToken()), 401);

        $lines = [];
        $gauge = function (string $name, string $help, array $samples) use (&$lines) {
            $lines[] = "# HELP $name $help";
            $lines[] = "# TYPE $name gauge";
            foreach ($samples as $labels => $value) {
                $lines[] = $name.($labels === '' ? '' : '{'.$labels.'}').' '.$value;
            }
        };

        $byStatus = Lead::query()->selectRaw('status, count(*) as c')->groupBy('status')->pluck('c', 'status');
        $samples = [];
        foreach (Lead::STATUSES as $s) {
            $samples['status="'.$s.'"'] = (int) ($byStatus[$s] ?? 0);
        }
        $gauge('console_leads', 'Leads by review status', $samples);
        $gauge('console_conversations', 'Stored conversations', ['' => Conversation::count()]);
        $gauge('console_evaluation_runs', 'Recorded evaluation runs', ['' => EvaluationRun::count()]);

        $byType = AuditEvent::query()->selectRaw('type, count(*) as c')->groupBy('type')->pluck('c', 'type');
        $samples = [];
        foreach (AuditEvent::TYPES as $t) {
            $samples['type="'.$t.'"'] = (int) ($byType[$t] ?? 0);
        }
        $gauge('console_audit_events', 'Audit events by type', $samples);

        return response(implode("\n", $lines)."\n", 200, ['Content-Type' => 'text/plain; version=0.0.4']);
    }
}
