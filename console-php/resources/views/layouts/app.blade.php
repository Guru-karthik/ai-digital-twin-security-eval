<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>@yield('title', 'Console') · Twin console</title>
<link rel="stylesheet" href="/console.css">
</head>
<body>
@auth
<header>
  <nav>
    <a href="{{ route('leads.index') }}">Leads</a>
    <a href="{{ route('conversations.index') }}">Conversations</a>
    <a href="{{ route('runs.index') }}">Evaluation runs</a>
    <a href="{{ route('audit.index') }}">Audit log</a>
  </nav>
  <span>{{ auth()->user()->email }} ({{ auth()->user()->role }})</span>
  <form class="inline" method="POST" action="{{ route('logout') }}">@csrf<button type="submit">Sign out</button></form>
</header>
@endauth
<main>
@if (session('status'))<div class="flash" role="status">{{ session('status') }}</div>@endif
@yield('content')
</main>
</body>
</html>
