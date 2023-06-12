from openbabel import pybel
import os
import shutil


class DockingJob:

    def __init__(self, receptor='1_input_files/receptor/' + os.listdir('1_input_files/receptor/')[0], ligands='2_ligprep_job/job/' + [x for x in os.listdir('2_ligprep_job/job/') if x.endswith('.sdf')][0]):

        self.receptor = receptor.split('/')[-1]
        self.ligands = ligands.split('/')[-1]
        self.docking_tool = None
        self.grid_file = None
        self.reference_ligand = None

        self._ligandsChecker(ligands)
        self._folderPreparation()

    def _ligandsChecker(self, ligands):

        if (ligands.split('.')[-1] != 'sdf') or (ligands.split('.')[-1] != 'sd'):
            pass
        else:
            raise Exception(
                'LigandsFileError: The ligands file shoud be the output from ligprep in sdf format.')

    def _folderPreparation(self):

        if not os.path.isdir('3_docking_job'):
            os.mkdir('3_docking_job')

        if not os.path.isdir('3_docking_job/job'):
            os.mkdir('3_docking_job/job')

    def _glidePrepareJob(self, grid_file, forcefield):

        shutil.copy(grid_file, '3_docking_job/job')
        shutil.copy('2_ligprep_job/job/' + self.ligands, '3_docking_job/job')

        with open('3_docking_job/job/glide_job.in', 'w') as filein:
            filein.writelines([
                'FORCEFIELD   {}\n'.format(forcefield),
                'GRIDFILE   {}\n'.format(grid_file),
                'LIGANDFILE   {}\n'.format(self.ligands),
                'PRECISION   SP\n'
            ])

        print(' - Glide job generated successfully with grid {grid} and forcefield {ff}.'.format(
            grid=grid_file, ff=forcefield))

    def _rdockReceptorFormatChecker(self, receptor):

        if len(receptor.split('.')) == 2:
            receptor_name, receptor_format = receptor.split('.')

        else:
            raise Exception(
                'ReceptorNameError: Receptor name should only have one dot separating the name and the format.')

        if receptor_format != 'mol2':

            print(' - Changing receptor\'s format to mol2.')
            receptor_generator = pybel.readfile(
                receptor_format, '1_input_files/receptor/' + receptor)
            receptor_molecule = next(receptor_generator)
            receptor_molecule.write(
                "mol2", "3_docking_job/job/{}.mol2".format(receptor_name), overwrite=True)

        else:
            pass

    def _rdockFileCopier(self, reference_ligand):
        shutil.copy(reference_ligand, '3_docking_job/job')
        shutil.copy('2_ligprep_job/job/' + self.ligands, '3_docking_job/job')
        shutil.copy('1_input_files/receptor/' +
                    self.receptor, '3_docking_job/job')

    def _rdockParamFilesWriter(self, receptor, reference_ligand):

        print(' - Using {} as reference ligand to generated cavity and grid.'.format(reference_ligand))

        parameter_file = os.path.join(
            '3_docking_job/job', 'parameter_file.prm')

        if not os.path.isfile(parameter_file):
            with open(parameter_file, 'w') as fileout:
                fileout.writelines(
                    'RBT_PARAMETER_FILE_V1.00\n'
                    'TITLE rdock\n'
                    '\n'
                    'RECEPTOR_FILE ' + receptor + '\n'
                    'RECEPTOR_FLEX 3.0\n'
                    '\n'
                    '##################################################################\n'
                    '### CAVITY DEFINITION: REFERENCE LIGAND METHOD\n'
                    '##################################################################\n'
                    'SECTION MAPPER\n'
                    '    SITE_MAPPER RbtLigandSiteMapper\n'
                    '    REF_MOL ' + reference_ligand + '\n'
                    '    RADIUS 6.0\n'
                    '    SMALL_SPHERE 1.0\n'
                    '    MIN_VOLUME 100\n'
                    '    MAX_CAVITIES 1\n'
                    '    VOL_INCR 0.0\n'
                    '   GRIDSTEP 0.5\n'
                    'END_SECTION\n'
                    '\n'
                    '#################################\n'
                    '#CAVITY RESTRAINT PENALTY\n'
                    '#################################\n'
                    'SECTION CAVITY\n'
                    '    SCORING_FUNCTION RbtCavityGridSF\n'
                    '    WEIGHT 1.0\n'
                    'END_SECTION\n')

    def _rdockGridGenerator(self):

        if not os.path.isdir('3_docking_job/job/runs'):
            os.mkdir('3_docking_job/job/runs')

        with open('3_docking_job/job/runs/grid.sh', 'w') as fileout:
            fileout.writelines(
                'rbcavity -was -d -r parameter_file.prm > parameter_file.log\n'
            )

    def _rdockJobSplitter(self, ligands, cpus_docking):

        print(' - Splitting {ligands_file}\'s molecules into {cpus} different files.'.format(
            ligands_file=ligands, cpus=cpus_docking))

        # Generating split file
        if not os.path.isfile('3_docking_job/job/splitMols.sh'):
            with open('3_docking_job/job/splitMols.sh', 'w') as filein:
                filein.writelines(
                    '#!/bin/bash\n'
                    '#Usage: splitMols.sh <input> #Nfiles <outputRoot>\n'
                    'module load rdock\n'
                    'fname=$1\n'
                    'nfiles=$2\n'
                    'output=$3\n'
                    'molnum=$(grep -c \'$$$$\' $fname)\n'
                    'echo " - $molnum molecules found"\n'
                    'echo " - Dividing \'$fname\' into $nfiles files"\n'
                    'rawstep=`echo $molnum/$nfiles | bc -l`\n'
                    'let step=$molnum/$nfiles\n'
                    'if [ ! `echo $rawstep%1 | bc` == 0 ]; then\n'
                    '        let step=$step+1;\n'
                    'fi;\n'
                    'sdsplit -$step -o$output $1\n'
                )

        # Generating splitted ligand files
        with open('3_docking_job/job/runs/split.sh', 'w') as fileout:
            fileout.writelines(
                '../splitMols.sh ../{ligands_file} {cpus} ../ligands\n'.format(
                    ligands_file=ligands, cpus=cpus_docking)
            )

    def _rdockRunFilesGenerator(self, cpus_docking):

        # Generating folders
        if not os.path.isdir('3_docking_job/job/ligands'):
            os.mkdir('3_docking_job/job/ligands')

        if not os.path.isdir('3_docking_job/job/results'):
            os.mkdir('3_docking_job/job/results')

        # Generating run files
        for i in range(1, cpus_docking+1):
            with open('3_docking_job/job/runs/run{}'.format(i), 'w') as fileout:
                fileout.writelines([
                    '#!/bin/sh\n',
                    '#SBATCH --job-name=rdock' + str(i) + ' \n',
                    '#SBATCH --time=01:00:00\n',
                    '#SBATCH --ntasks=1\n',
                    '#SBATCH --output=rdock.out\n',
                    '#SBATCH --error=rdock.err\n',
                    '\n',
                    'module load rdock\n',
                    'module load ANACONDA/2019.10\n',
                    'module load intel\n',
                    'module load mkl\n',
                    'module load impi\n',
                    'module load gcc\n',
                    'module load boost/1.64.0\n',
                    '\n',
                    '\n',
                    'rbdock -i ../ligands/split{val}.sd -o ../results/split{val}_out -r ../parameter_file.prm -p dock.prm -n 50\n'.format(
                        val=i),
                    'done\n'
                ])

        with open('3_docking_job/job/run_prepare_rDock.sh', 'w') as fileout:
            fileout.writelines(
                '#!/bin/bash\n'
                '# Run runs/run_grid.sh\n'
                'source runs/run_grid.sh\n'
                '\n'
                '# Run runs/run_split.sh\n'
                'source runs/run_split.sh\n'
            )

        with open('3_docking_job/job/run_rDock.sh', 'w') as fileout:
            fileout.writelines(
                '#!/bin/bash\n'
                'for d in run*; do echo ${d}; sbatch ${d}; done'
            )

        print(' - RDock docking job generated successfully to run with {} cpus.'.format(cpus_docking))

    def _equibindReceptorFormatChecker(self, receptor):

        if len(receptor.split('.')) == 2:
            receptor_name, receptor_format = receptor.split('.')

        else:
            raise Exception(
                'ReceptorNameError: Receptor name should only have one dot separating the name and the format.')

        if receptor_format != 'pdb':
            print(' - Changing receptor\'s format to pdb.')

            receptor_generator = pybel.readfile(
                receptor_format, '1_input_files/receptor/' + receptor)
            receptor_molecule = next(receptor_generator)
            receptor_molecule.write(
                "pdb", "3_docking_job/{}.pdb".format(receptor_name), overwrite=True)

        else:
            shutil.copy('1_input_files/receptor/' + receptor, '3_docking_job')

    def _equibindSplitLigands(self, ligands):

        with open('2_ligprep_job/job/{}'.format(ligands), 'r') as f:
            content = f.read().strip()

        records = content.split('$$$$')

        for record in records:
            if record.strip():

                # Extract the value of the property for naming the output file
                variant_value = None
                lines = record.split('\n')
                for line in lines:
                    if '<s_lp_Variant>' in line:
                        variant_value = lines[lines.index(line) + 1]
                        break

                if variant_value:
                    output_file = variant_value + '.sdf'

                    if not os.path.isdir('3_docking_job/job/equibind_calculations'):
                        os.mkdir('3_docking_job/job/equibind_calculations')

                    if not os.path.isdir('3_docking_job/job/equibind_results'):
                        os.mkdir('3_docking_job/job/equibind_results')

                    if not os.path.isdir('3_docking_job/job/equibind_calculations/{}'.format(variant_value)):
                        os.mkdir(
                            '3_docking_job/job/equibind_calculations/{}'.format(variant_value))

                    # Write the record to the output file
                    with open('3_docking_job/job/equibind_calculations/{folder}/{output}'.format(folder=variant_value, output=output_file), 'w') as f:
                        f.write(record + '$$$$')

    def _equibindFolderPreparation(self, receptor):
        for folder in os.listdir('3_docking_job/job/equibind_calculations'):
            folder_path = os.path.join(
                '3_docking_job/job/equibind_calculations', folder)

            if os.path.isdir(folder_path):
                destination_protein = os.path.join(
                    folder_path, folder + "_protein.pdb")
                destination_ligands = os.path.join(
                    folder_path, folder + "_ligand.sdf")

                shutil.copyfile(
                    '3_docking_job/{}'.format(receptor), destination_protein)
                os.rename('3_docking_job/job/equibind_calculations/{name}/{name}.sdf'.format(
                    name=folder), destination_ligands)

    def _equibindFilesPreparation(self):

        with open('3_docking_job/job/run', 'w') as fileout:
            fileout.writelines(
                '#!/bin/bash\n'
                '#SBATCH --job-name=equi\n'
                '#SBATCH --time=1:00:00\n'
                '#SBATCH --gres gpu:1\n'
                '#SBATCH --cpus-per-task=40\n'
                '#SBATCH --ntasks=1\n'
                '#SBATCH --output=equi.out\n'
                '#SBATCH --error=equi.err\n'
                '\n'
                'module purge\n'
                'module load anaconda3/2020.02\n'
                'module list\n'
                '\n'
                'eval "$(conda shell.bash hook)"\n'
                'conda activate /apps/ANACONDA3/2020.02/envs/ESM-EquiBind-DiffDock\n'
                '\n'
                'cp -r /gpfs/apps/POWER9/ANACONDA3/2020.02/envs/ESM-EquiBind-DiffDock/modules/EquiBind/runs .'
                'python /gpfs/apps/POWER9/ANACONDA3/2020.02/envs/ESM-EquiBind-DiffDock/modules/EquiBind/inference.py --config=inference.yml\n'
            )

        with open('3_docking_job/job/inference.yml', 'w') as fileout:
            fileout.writelines(
                'run_dirs:\n'
                '  - flexible_self_docking # the resulting coordinates will be saved here as tensors in a .pt file (but also as .sdf files if you specify an "output_directory" below)\n'
                'inference_path: \'equibind_calculations\' # this should be your input file path as described in the main readme\n'
                '\n'
                'test_names: timesplit_test\n'
                'output_directory: \'equibind_results\' # the predicted ligands will be saved as .sdf file here\n'
                'run_corrections: True\n'
                'use_rdkit_coords: False # generates the coordinates of the ligand with rdkit instead of using the provided conformer. If you already have a 3D structure that you want to use as initial conformer, then leave this as False\n'
                'save_trajectories: False\n'
                '\n'
                'num_confs: 1 # usually this should be 1\n'
            )

        print(' - Equibind docking job created successfully.')

    def setGlideDocking(self, grid_file, forcefield='OPLS_2005'):

        self.grid_file = grid_file
        self.docking_tool = 'glide'

        self._glidePrepareJob(grid_file, forcefield)

    def setRdockDocking(self, reference_ligand, ligands, cpus_docking):

        self.reference_ligand = reference_ligand
        self.docking_tool = 'rdock'

        self._rdockReceptorFormatChecker(self.receptor)
        self._rdockFileCopier(reference_ligand)
        self._rdockParamFilesWriter(self.receptor, self.reference_ligand)
        self._rdockGridGenerator()
        self._rdockJobSplitter(ligands, cpus_docking)
        self._rdockRunFilesGenerator(cpus_docking)

    def setEquibindDocking(self, ligands, receptor):

        self.docking_tool = 'equibind'

        self._equibindReceptorFormatChecker(receptor)
        self._equibindSplitLigands(ligands)
        self._equibindFolderPreparation(receptor)
        self._equibindFilesPreparation()
