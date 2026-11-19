@extends('layouts.app')
@section('title', 'Conversation '.$conversation->id)
@section('content')
<p><a href="{{ route('conversations.index') }}">&larr; Conversations</a></p>
<h1>Conversation {{ $conversation->external_id }}</h1>
<p>Defense: {{ $conversation->defense ?? 'n/a' }} · Model: {{ $conversation->model ?? 'n/a' }}</p>
@foreach ($conversation->messages as $m)
<div class="msg {{ $m['role'] === 'user' ? 'user' : '' }}"><strong>{{ $m['role'] }}</strong><br>{{ $m['content'] }}</div>
@endforeach
@endsection
