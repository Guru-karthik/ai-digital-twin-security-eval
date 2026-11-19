@extends('layouts.app')
@section('title', 'Evaluation runs')
@section('content')
<h1>Evaluation runs</h1>
<div class="scroll"><table>
<thead><tr><th>Run</th><th>Defense</th><th>Model</th><th>Passed</th><th>ASR</th><th>Mean latency (s)</th><th>Cost (USD)</th><th>Failed checks</th></tr></thead>
<tbody>
@forelse ($runs as $r)
<tr><td>{{ $r->run_key }}</td><td>{{ $r->defense }}</td><td>{{ $r->model }}</td><td>{{ $r->passed_cases }}/{{ $r->total_cases }}</td>
<td>{{ $r->attack_success_rate !== null ? number_format($r->attack_success_rate * 100, 1).'%' : 'n/a' }}</td>
<td>{{ $r->mean_latency_s !== null ? number_format($r->mean_latency_s, 2) : 'n/a' }}</td>
<td>{{ $r->cost_usd !== null ? number_format($r->cost_usd, 4) : 'n/a' }}</td>
<td>{{ implode(', ', $r->failed_checks ?? []) }}</td></tr>
@empty
<tr><td colspan="8">No runs.</td></tr>
@endforelse
</tbody></table></div>
@include('layouts.pager', ['paginator' => $runs])
@endsection
