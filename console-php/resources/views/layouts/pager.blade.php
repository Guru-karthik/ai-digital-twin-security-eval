<div class="pager">
  @if ($paginator->previousPageUrl())<a href="{{ $paginator->previousPageUrl() }}">&larr; Newer</a>@endif
  @if ($paginator->nextPageUrl())<a href="{{ $paginator->nextPageUrl() }}">Older &rarr;</a>@endif
</div>
