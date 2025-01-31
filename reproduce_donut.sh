python main.py -ep 500 -bs 64 -nexp 10 -sm binary -env donut -net linear # Full
python main.py -ep 500 -bs 64 -nexp 10 -sm reset-binary -env donut -net linear # Min
python main.py -ep 500 -bs 64 -nexp 10 -sm equal-binary -env donut -net linear # Reset
python main.py -ep 500 -bs 64 -nexp 10 -sm binary -env donut -net linear -nomem True # No Memory
python main.py -ep 500 -bs 256 -nexp 10 -sm rnn -env donut -net rnn -lr 0.002 # RNN
python main.py -ep 500 -bs 2048 -nexp 10 -sm binary -cf True -env donut -net linear # FairQCM
python create_plots.py --env donut --root datasets/donut --smooth 10 --std False