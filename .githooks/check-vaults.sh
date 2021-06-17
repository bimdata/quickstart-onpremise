#! /bin/bash

# Redirect script output to stderr.
exec 1>&2

if git rev-parse --verify HEAD >/dev/null 2>&1 ; then
	against=HEAD
else
	# Initial commit: diff against an empty tree object
	against=$(git hash-object -t tree /dev/null)
fi

unencrypted_vault=()
vault_file_pattern='*vault.yml$'
exit_code=0

while IFS= read -r -d $'\0' file ; do
	# Skip non-vault files
	echo $file | grep -qE $vault_file_pattern || continue

	# Get file status
	file_status=$(git status --porcelain -- "$file" 2> /dev/null)
	file_status_index=$(echo $file_status | cut -c1)
	file_status_worktree=$(echo $file_status | cut -c2)

	# Skip deleted files
	[[ "$file_status_index" == 'D' ]] && continue

	# Error when commited vault files are also modified in the worktree
	# because we can't check if the commited version are encrypt.
	if [[ "$file_status_worktree"  != " " ]] ; then
		echo "File $file is modified in the worktree. Can't check if the commited version is encrypt."
		exit_code=1
		continue
	fi

	# Check if file is an encrypted vault
	if ! head -1 "$file" | grep --quiet '^\$ANSIBLE_VAULT;' ; then
		unencrypted_vault+=("$file")
		exit_code=1
	fi
done < <(git diff --cached --name-only -z "$against")

# Print unencrypted vault files and exit
if [[ "${#unencrypted_vault[@]}" -gt "0" ]] ; then
	echo "Unencrypted vault: "
	for file in ${unencrypted_vault[@]} ; do
		echo " - $file"
	done
fi
exit $exit_code
