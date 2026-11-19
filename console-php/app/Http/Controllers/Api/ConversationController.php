<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Conversation;
use Illuminate\Http\Request;

class ConversationController extends Controller
{
    use Paginates;

    public function index(Request $request)
    {
        // messages are omitted from the list view
        return $this->paginated(Conversation::query()->select(
            ['id', 'external_id', 'defense', 'model', 'message_count', 'created_at']), $request);
    }

    public function show(Conversation $conversation)
    {
        return $conversation;
    }

    public function store(Request $request)
    {
        $data = $request->validate([
            'external_id' => ['required', 'string', 'max:255', 'unique:conversations,external_id'],
            'defense' => ['sometimes', 'nullable', 'string', 'max:32'],
            'model' => ['sometimes', 'nullable', 'string', 'max:100'],
            'messages' => ['required', 'array', 'max:200'],
            'messages.*.role' => ['required', 'in:user,assistant'],
            'messages.*.content' => ['required', 'string', 'max:8000'],
        ]);
        $data['message_count'] = count($data['messages']);

        return response()->json(Conversation::create($data)->refresh()->makeHidden('messages'), 201);
    }
}
