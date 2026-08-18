# Rejected candidate evidence

This directory contains generated C bodies that failed compilation or the
pre-build review gate. They are retained because the failure and attempted
shape can prevent a full model retry after declarations, members, or other
blocking context become known.

Rejected bodies are not permuter seeds until they compile. Their queue records
must retain the rejection reason, and the root agent stages each file by
explicit path in the same work batch that records the outcome.
