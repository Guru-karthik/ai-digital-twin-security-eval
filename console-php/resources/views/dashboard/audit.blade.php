@extends('layouts.app')
@section('title', 'Audit log')
@section('content')
<h1>Audit log</h1>
<p>Records decisions the agent and gateway made, plus admin actions taken in this console.</p>
<div class="scroll"><table>
<thead><tr><th>#</th><th>When</th><th>Type</th><th>Actor</th><th>Subject</th><th>Detail</th></tr></thead>
<tbody>
@forelse ($events as $e)
<tr><td>{{ $e->id }}</td><td>{{ $e->created_at }}</td><td>{{ $e->type }}</td><td>{{ $e->actor }}</td><td>{{ $e->subject }}</td><td>{{ json_encode($e->detail) }}</td></tr>
@empty
<tr><td colspan="6">No events.</td></tr>
@endforelse
</tbody></table></div>
@include('layouts.pager', ['paginator' => $events])
@endsection
