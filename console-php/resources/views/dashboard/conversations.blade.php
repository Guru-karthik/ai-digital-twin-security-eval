@extends('layouts.app')
@section('title', 'Conversations')
@section('content')
<h1>Conversations</h1>
<div class="scroll"><table>
<thead><tr><th>#</th><th>External id</th><th>Defense</th><th>Model</th><th>Messages</th><th>Created</th></tr></thead>
<tbody>
@forelse ($conversations as $c)
<tr><td><a href="{{ route('conversations.show', $c) }}">{{ $c->id }}</a></td><td>{{ $c->external_id }}</td><td>{{ $c->defense }}</td><td>{{ $c->model }}</td><td>{{ $c->message_count }}</td><td>{{ $c->created_at }}</td></tr>
@empty
<tr><td colspan="6">No conversations.</td></tr>
@endforelse
</tbody></table></div>
@include('layouts.pager', ['paginator' => $conversations])
@endsection
