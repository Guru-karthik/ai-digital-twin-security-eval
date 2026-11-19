@extends('layouts.app')
@section('title', 'Leads')
@section('content')
<h1>Leads</h1>
<p>Filter:
  <a href="{{ route('leads.index') }}">all</a> ·
  @foreach (\App\Models\Lead::STATUSES as $s)<a href="{{ route('leads.index', ['status' => $s]) }}">{{ $s }}</a> @endforeach
</p>
<div class="scroll"><table>
<thead><tr><th>#</th><th>Email</th><th>Name</th><th>Notes</th><th>Status</th><th>Created</th>@if (auth()->user()->isAdmin())<th>Review</th>@endif</tr></thead>
<tbody>
@forelse ($leads as $lead)
<tr>
  <td>{{ $lead->id }}</td><td>{{ $lead->email }}</td><td>{{ $lead->name }}</td><td>{{ $lead->notes }}</td>
  <td><span class="badge {{ $lead->status }}">{{ $lead->status }}</span></td><td>{{ $lead->created_at }}</td>
  @if (auth()->user()->isAdmin())
  <td>@if ($lead->status === 'pending')
    @foreach (['approved' => 'Approve', 'rejected' => 'Reject'] as $value => $label)
    <form class="inline" method="POST" action="{{ route('leads.review', $lead) }}">@csrf<input type="hidden" name="status" value="{{ $value }}"><button type="submit">{{ $label }}</button></form>
    @endforeach
  @endif</td>
  @endif
</tr>
@empty
<tr><td colspan="7">No leads.</td></tr>
@endforelse
</tbody></table></div>
@include('layouts.pager', ['paginator' => $leads])
@endsection
