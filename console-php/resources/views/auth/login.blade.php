@extends('layouts.app')
@section('title', 'Sign in')
@section('content')
<form class="card" method="POST" action="/login">
  @csrf
  <h1>Sign in</h1>
  <label for="email">Email</label>
  <input id="email" name="email" type="email" value="{{ old('email') }}" autocomplete="username" required autofocus>
  <label for="password">Password</label>
  <input id="password" name="password" type="password" autocomplete="current-password" required>
  @error('email')<p class="err" role="alert">{{ $message }}</p>@enderror
  <p><button type="submit">Sign in</button></p>
</form>
@endsection
